import json
import hmac
import hashlib
import datetime
import re, sys, os
import copy
import urllib2

class EvidentApi:

    #
    # Class variables.
    #

    __evidentApiObjects = None
    __secretKey = None
    __publicKey = None
    __baseUrl = None
    __basePath = None

    #
    # Class methods.
    #

    def __init__(self, secretKey, publicKey, apiFilePath = 'ApiMap.json', baseUrl = 'https://api.evident.io', basePath = '/api/v2/', verbose = False):

        #
        # Set class varibles.
        #

        self.__secretKey = secretKey
        self.__publicKey = publicKey
        self.__baseUrl = baseUrl
        self.__basePath = basePath
        self.__verbose = verbose

        #
        # Load API map.
        #

        self.__LoadApiMapFile(apiFilePath)

        #
        # Verify settings.
        #

        self.__Verify()

    def __Verify(self):
        everythingIsGood = True

        #
        # Check secret key.
        #

        if not self.__secretKey or not re.match('\S{88}', self.__secretKey):
            print 'ERROR: Invalid secret key'
            everythingIsGood = False

        #
        # Check public key.
        #

        elif not self.__publicKey or not re.match('\S{88}', self.__publicKey):
            print 'ERROR: Invalid public secret key'
            everythingIsGood = False

        #
        # Check evident API objects.
        #

        elif not self.__evidentApiObjects or len(self.__evidentApiObjects) < 1:
            print 'ERROR: No api objects loaded into __evidentApiObjects'
            everythingIsGood = False

        #
        # Check if base and path URL.
        #

        elif not self.__baseUrl or not self.__basePath:
            print 'ERROR: Invalid base or path url settings'
            everythingIsGood = False

        #
        # Check connection.
        #

        elif not (self.__CallEvident('GET', 'users', returnOnERROR = True)):
            print 'ERROR: API access check failed'
            everythingIsGood = False

        #
        # Is everything good?
        #

        if not (everythingIsGood):
            print "ERROR: Settings verification failed"
            sys.exit(1)
        else:
            if self.__verbose:
                print "Verification Passed"

    #
    # Class functions.
    #

    def __LoadApiMapFile(self, mappingFilePath):
        self.__evidentApiObjects = None

        #
        # Check if file exists.
        #

        if not os.path.exists(mappingFilePath):
            print 'ERROR: Invalid mappings file path: {0}'.format(mappingFilePath)
            sys.exit(1)

        #
        # Read JSON file.
        #

        jsonfile = open(mappingFilePath)
        json_data = jsonfile.read()
        jsonfile.close()

        #
        # Get and convert settings to Python format.
        #

        orgData = json.loads(json_data)
        settings = orgData["settings"]

        #
        # Replace JSON setting markers in API mapping.
        #

        for setting in settings:
            jsonSettingValue = json.dumps(settings[setting])
            json_data = re.sub('\"\<{0}\>\"'.format(setting), jsonSettingValue, json_data)

        #
        # Get final data mapping data (in Python format)
        #

        self.__evidentApiObjects = json.loads(json_data)['mappings']

    def __CallEvident(self, restMethod, urlPath, data = '', returnOnERROR = False):

        #
        # Create required meta data request
        #

        urlPath =  self.__basePath + urlPath
        contentType = 'application/vnd.api+json'
        dataMD5 = self.__DataToMD5(data)
        currentDateTime = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        canonicalStr = '{0},{1},{2},{3}'.format(contentType, dataMD5, urlPath, currentDateTime)
        encodeString = self.__GetEncodeString(canonicalStr, self.__secretKey)

        #
        # Create header content and connection objects.
        #

        opener = urllib2.build_opener(urllib2.HTTPHandler)
        completeUrl = self.__baseUrl + urlPath
        request = urllib2.Request(completeUrl, data = data)
        request.add_header('Accept', 'application/vnd.api+json')
        request.add_header('Content-Type', contentType)
        request.add_header('Content-MD5', dataMD5)
        request.add_header('Authorization', 'APIAuth {0}:{1}'.format(self.__publicKey, encodeString))
        request.add_header('Date', currentDateTime)
        request.get_method = lambda: restMethod.upper()

        #
        # Send request.
        #

        result = None
        try:

            #
            # Execute HTTP request and record time.
            #

            startTime = datetime.datetime.now()
            result = opener.open(request)
            runtime = (datetime.datetime.now() - startTime)
            result = result.read()

            #
            # Write execute time and other information to log file.
            #

            if self.__verbose:
                print 'URL: {0}\nTYPE: {1}\nBYTES SENT: {2}\nBYTES RECEIVED: {3}\nDATASENT: {4}\nRESPONSE: {5}\nRUNTIME: {6}\nTIME: {7}\n\n'\
                .format(completeUrl, restMethod.upper(), len(str(data)) * 4, len(str(result)) * 4, data, result, runtime, startTime)

        #
        # Capture error.
        #

        except urllib2.URLError, e:
            print 'URL:{0}\nTYPE: {1}\nDATASENT: {2}\nTIME: {3}\n\n'\
            .format(completeUrl, restMethod.upper(), data, startTime)
            print 'API ERROR: {0}\n{1}'.format(e, completeUrl)
            if returnOnERROR:
                return None
            sys.exit(1)

        #
        # Return result
        #

        return result

    def __CreateApiFuction(self, apiObjectName):

        #
        # Check if API object name exists.
        #

        if not apiObjectName in self.__evidentApiObjects:
            print 'CreateApiFuction ERROR: API does not exist: {0}'.format(apiObjectName)
            sys.exit(1)

        #
        # Create API function.
        #

        def ApiFunction(*args, **kwargs):

            #
            # Copy data object.
            #

            apiObject = copy.deepcopy(self.__evidentApiObjects[apiObjectName])

            #
            # Get Body attribute data structure
            #

            if ('Data Structure' in apiObject) and (not apiObject['Data Structure'] is None) and ('attributes' in apiObject['Data Structure']):
                attributeDict = apiObject['Data Structure']['attributes']
                payload = { "data":
                    { "attributes":
                        attributeDict
                    }
                }
            else:
                attributeDict = {}
                payload = ''

            #
            # Process URL and Body attribute arguments.
            #

            for argKey in kwargs:

                #
                # Check and replace URL attributes.
                #

                orgStr = apiObject['Path']
                apiObject['Path'] = re.sub('\[{0}\]'.format(argKey), str(kwargs[argKey]), apiObject['Path'])
                if not orgStr == apiObject['Path']:
                    continue

                #
                # Check and replace Body attributes.
                #

                found = False
                for attribute in attributeDict:
                    if (attribute == argKey):
                        attributeDict[attribute] = kwargs[argKey]
                        found = True
                        break

                #
                # Check if we found attribute argument.
                #

                if not found:
                    print 'ERROR: Did not find argument: {0}'.format(argKey)
                    sys.exit(1)

            #
            # Call evident.
            #

            return self.__CallEvident(apiObject['Request Type'], apiObject['Path'], json.dumps(payload))
        return ApiFunction

    def __getattr__(self, apiObjectName):
        if not apiObjectName in self.__evidentApiObjects:
            print 'API call {0} not found'.format(apiObjectName)
        function = self.__CreateApiFuction(apiObjectName)
        self.__dict__[apiObjectName] = function
        return function

    def __GetEncodeString(self, canonicalStr, secretKey):
        hashed = hmac.new(secretKey, canonicalStr, hashlib.sha1)
        return hashed.digest().encode("base64").rstrip('\n')

    def __DataToMD5(self, data):
        if not data:
            return ''
        md5 = hashlib.md5()
        md5.update(data)
        return md5.digest().encode("base64").rstrip('\n')
