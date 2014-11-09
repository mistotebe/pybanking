from Crypto.Hash import SHA256

class KeyLockedError(Exception):
    pass

class Key(object):
    hash_algo = SHA256
    hash_name = 'sha256'

    fingerprint = None

    @property
    def locked(self):
        raise NotImplementedError

    def unlock(self, passphrase):
        raise NotImplementedError

    def digest(self, message):
        return self.hash_algo.new(message)

    def _sign(self, hash_name, digest):
        raise NotImplementedError

    def sign(self, message):
        if self.locked:
            raise KeyLockedError("Please unlock the key")

        digest = self.digest(message)
        return self._sign(self.hash_name, digest)
