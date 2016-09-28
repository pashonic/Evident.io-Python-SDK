from Evident import EvidentApi

secretKey = ''
publicKey = ''
evidentApi = EvidentApi(secretKey, publicKey)
print evidentApi.ListSignatures()
print evidentApi.ListSeppressions()
