from hashlib import sha256

def sha256_encode(text):
    '''
        Function that encodes a given text to SHA256
    '''
    text = text.encode('utf-8')
    sha_obj = sha256(text)
    return sha_obj.hexdigest()



#https://www.debugpointer.com/python/create-sha256-hash-of-a-string-in-python