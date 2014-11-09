from base64 import b64decode
from xml.dom.minidom import parse, parseString

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Hash.HMAC import HMAC
from Crypto.Protocol.KDF import PBKDF2
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

from .key import Key, KeyLockedError

XMLENC_NS_URL = "http://www.w3.org/2001/04/xmlenc#"
PKCS5_NS_URL = "http://www.rsasecurity.com/rsalabs/pkcs/schemas/pkcs-5v2-0#"

def removeIgnorableWhitespace(document):
    children = list(document.childNodes)
    for node in children:
        if node.nodeType == node.TEXT_NODE and \
                not node.nodeValue.strip():
            document.removeChild(node)
        else:
            removeIgnorableWhitespace(node)
    return document

class NativeKey(Key):
    def __init__(self, name):
        self._publicKey = None
        self._privateKey = None

        self.name = name
        self._container = removeIgnorableWhitespace(parse(name))

    @property
    def locked(self):
        return self._privateKey is None

    def unlock(self, passphrase):
        # might eventually implement the following as specced and in a separate module:
        # http://www.w3.org/TR/2002/REC-xmlenc-core-20021210/Overview.html#aes256-cbc
        # http://www.w3.org/2008/xmlsec/Drafts/derived-key/derived-keys.xml
        # https://tools.ietf.org/html/rfc4051
        # https://tools.ietf.org/html/rfc6030
        # http://www.opensource.apple.com/source/libsecurity_asn1/libsecurity_asn1-29908/asn1/pkcs5.asn1
        if self._privateKey:
            return

        encryption_elem = self._container.getElementsByTagNameNS(XMLENC_NS_URL, 'EncryptionMethod')[0]

        # jumping over the structure at the moment, see above
        derivation_func = PBKDF2

        params_elem = encryption_elem.getElementsByTagNameNS(PKCS5_NS_URL, 'Parameters')[0]

        salt_elem = params_elem.getElementsByTagNameNS(PKCS5_NS_URL, 'Salt')[0]
        IV = salt = b64decode(salt_elem.firstChild.firstChild.nodeValue)

        iterations_elem = params_elem.getElementsByTagNameNS(PKCS5_NS_URL, 'IterationCount')[0]
        iterations = int(iterations_elem.firstChild.nodeValue)

        key_length_elem = params_elem.getElementsByTagNameNS(PKCS5_NS_URL, 'KeyLength')[0]
        key_length = int(key_length_elem.firstChild.nodeValue)
        assert key_length % 8 == 0

        prf = lambda p, s: HMAC(p, s, SHA256).digest()

        key = derivation_func(passphrase, salt, count=iterations, dkLen=(key_length//8), prf=prf)

        encryption_scheme = AES
        encryption_mode = AES.MODE_CBC

        decryptor = encryption_scheme.new(key, mode=encryption_mode, IV=IV)

        # then the encrypted data
        key_elem = self._container.getElementsByTagNameNS(XMLENC_NS_URL, 'CipherValue')[0]
        ciphertext_elem = key_elem.firstChild

        ciphertext = b64decode(ciphertext_elem.nodeValue)

        padded_plaintext = decryptor.decrypt(ciphertext)

        padlen = ord(padded_plaintext[-1])
        if padlen not in range(encryption_scheme.block_size) or \
                chr(padlen)*padlen != padded_plaintext[-padlen:]:
            raise KeyLockedError("Key decryption failed")

        plaintext = padded_plaintext[:-padlen]
        key_elem = removeIgnorableWhitespace(parseString(plaintext))

        keyparams = [RSA.bytes_to_long(b64decode(key_elem.getElementsByTagName(x)[0].firstChild.nodeValue)) for x in ['Modulus', 'Exponent', 'D', 'Q', 'P', 'InverseQ']]
        self._privateKey = RSA.construct(tuple(keyparams))
        self._publicKey = self._privateKey.publickey()
        self.fingerprint = SHA256.new(self._publicKey.exportKey(format='DER')).hexdigest()

    def _sign(self, name, digest):
        signer = PKCS1_v1_5.new(self._privateKey)
        return signer.sign(digest)
