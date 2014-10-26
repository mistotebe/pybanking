#!/usr/bin/env python

import urwid
import fioread

class SelectableText(urwid.Text):
    _selectable = True

    def keypress(self, size, key):
        return key

def main():
    palette = [
        ('header', 'light gray', 'black'),
        ('title', 'white', 'black'),
        ('focus', 'light gray,standout', 'black'),
        ]

    def exit_on_q(input):
        if input in ('q', 'Q'):
            raise urwid.ExitMainLoop()

    token = fioread.get_token()
    statement = fioread.FioConnection(token).last()

    info = statement.account
    header_text = [
        ('title', "Fio Statement Viewer"), " for ",
        ('account', info.accountId + "/" + info.bankId), " ",
        ('bold', info.dateStart[:10]), "-", ('bold', info.dateEnd[:10]), " ",
        "(", ('bold', str(info.openingBalance)), "-", ('bold', str(info.closingBalance)), ")",
        ]

    walker = urwid.SimpleFocusListWalker([])
    balance = info.openingBalance

    def wrap(text):
        w = SelectableText(text)
        w = urwid.AttrMap(w, {}, {None: 'focus'})
        return w

    for transaction in statement.transactions:
        transaction['balance'] = balance = balance + transaction.amount
        walker.append(wrap("%(date).10s %(balance)10s %(amount)10s %(currency)s %(comment)30s" % fioread.default(transaction)))

    header = urwid.AttrMap(urwid.Text(header_text), 'header')
    listbox = urwid.ListBox(walker)
    view = urwid.Frame(listbox, header=header)
    loop = urwid.MainLoop(view, palette, unhandled_input=exit_on_q)

    loop.run()

if __name__ == '__main__':
    main()
