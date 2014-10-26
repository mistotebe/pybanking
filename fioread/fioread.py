#!/usr/bin/env python

import sys
import os.path
import argparse
from urlparse import urljoin
import requests
import json

APPNAME='fioread'

parser = argparse.ArgumentParser()
parser.add_argument('--token', '-t')

class ConnectionError(Exception):
    pass


class DictWrapper(dict):
    def __init__(self, d):
        self.__dict = d

    def get(self, key, default=None):
        return self.__dict.get(key, default)

    def keys(self):
        return self.__dict.keys()

    def __setitem__(self, key, value):
        self.__dict[key] = value

    def __getitem__(self, key):
        return self.__dict[key]

    def __getattr__(self, name):
        return self.__dict[name]

class default(dict):
    def __init__(self, d, default=None):
        self.__dict = d
        self.__default = default

    def __getitem__(self, key):
        return self.__dict.get(key, self.__default)

def get_token():
    import xdg.BaseDirectory
    config_dirs = xdg.BaseDirectory.load_config_paths(APPNAME)
    for d in config_dirs:
        try:
            with open(os.path.join(d, 'token')) as token_file:
                return token_file.read().strip()
        except IOError:
            pass

    import getpass
    token = getpass.getpass(prompt='Your API token: ')

    config_dir = xdg.BaseDirectory.save_config_path(APPNAME)
    with open(os.path.join(config_dir, 'token'), 'w') as token_file:
        token_file.write(token)

    return token

class Account(DictWrapper):
    def __repr__(self):
        return "Account(%(accountId)s/%(bankId)s)" % self

class Transaction(DictWrapper):
    _mapping = {
        'column0': 'date',
        'column1': 'amount',
        'column2': 'account',
        'column3': 'sortcode',
        'column4': 'constant',
        'column5': 'variable',
        'column6': 'specific',
        'column7': 'user_comment',
        'column8': 'type',
        'column9': 'initiated_by',
        'column10': 'account_name',
        'column12': 'bank_name',
        'column14': 'currency',
        'column16': 'recipient_message',
        'column17': 'action_id',
        'column18': 'detailed_info',
        'column22': 'move_id',
        'column25': 'comment',
        'column26': 'swift_code',
    }

    def __init__(self, data):
        d = {}

        for name, value in data.items():
            if value is not None:
                try:
                    d[self._mapping[name]] = value['value']
                except KeyError:
                    print >>sys.stderr, 'Encountered unknown column: "%s" with name "%s"' % (name, value['name'])
        #for key, name in self._mapping.items():
        #    if data.has_key(key):
        #        d[name] = data[key]['value']
        super(Transaction, self).__init__(d)

    def __repr__(self):
        return "Transaction(%(move_id)s)" % self

class Statement(DictWrapper):
    def __init__(self, text):
        statement = json.loads(text)['accountStatement']
        self.account = Account(statement['info'])
        transactionList = statement.get('transactionList') or {}
        self.transactions = map(Transaction, transactionList.get('transaction') or [])

class FioConnection(object):
    BASE_URL="https://www.fio.cz/ib_api/rest/"

    def __init__(self, token):
        self._token = token

    def last(self):
        arguments = ['last', self._token, 'transactions.json']
        url = urljoin(self.BASE_URL, '/'.join(arguments))
        response = requests.get(url, verify=True)
        response.raise_for_status()

        return Statement(response.text)

if __name__ == '__main__':
    options = parser.parse_args()
    token = options.token or get_token()

    statement = FioConnection(token).last()

    print "Account %(accountId)s/%(bankId)s Period %(dateStart).10s(=%(openingBalance)f)-%(dateEnd).10s(=%(closingBalance)f)" % statement.account

    balance = statement.account.openingBalance
    for t in statement.transactions:
        t['balance'] = balance = balance + t.amount
        print "%(date).10s %(balance)10s %(amount)10s %(currency)s %(comment)30s" % default(t)
