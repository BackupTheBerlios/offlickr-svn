# Offlickr
# Hugo Haas -- mailto:hugo@larve.net -- http://larve.net/people/hugo/
# Homepage: http://larve.net/people/hugo/2005/12/offlickr/
# License: GPLv2

import sys
import libxml2
import urllib
import getopt
import time
import os.path

# Beej's Python Flickr API
# http://beej.us/flickr/flickrapi/
from flickrapi import FlickrAPI

__version__ = '0.3 - 2006-01-03 + DEV'
maxTime = '9999999999'

# Gotten from Flickr
flickrAPIKey = '1391fcd0a9780b247cd6a101272acf71'
flickrSecret = 'fd221d0336de3b6d'

class Offlickr:

    def __init__(self, key, secret, uid, browser = "lynx"):
        """Instantiates an Offlickr object
        An API key is needed, as well as an API secret and a user id.
        A browser can be specified to be used for authorizing the program
        to access the user account."""
        self.__flickrAPIKey = key
        self.__flickrSecret = secret
        # Get authentication token
        self.fapi = FlickrAPI(self.__flickrAPIKey, self.__flickrSecret)
        self.token = self.fapi.getToken(browser=browser)
        self.flickrUserId = uid

    def __testFailure(self, rsp):
        """Returns whether the previous API call was successful"""
        if rsp['stat'] == "fail":
            print "Error!"
            return True
        else:
            return False

    def getPhotoList(self, dateLo, dateHi):
        """Returns a list of photo given a time frame"""
        n = 0
        photos = [ ]

        while True:
            n = n + 1
            rsp = self.fapi.photos_search(api_key=self.__flickrAPIKey, auth_token=self.token,
                                          user_id = self.flickrUserId,
                                          per_page = "500", # Max allowed by Flickr
                                          page = str(n),
                                          min_upload_date = dateLo, max_upload_date = dateHi)
            if self.__testFailure(rsp):
                return None
            if rsp.photos[0]['total'] == '0':
                return None
            photos += rsp.photos[0].photo
            if len(photos) >= int(rsp.photos[0]['total']):
                break

        return photos

    def getPhotosetList(self):
        """Returns a list of photosets for a user"""

        rsp = self.fapi.photosets_getList(api_key=self.__flickrAPIKey, auth_token=self.token,
                                          user_id = self.flickrUserId)
        if self.__testFailure(rsp):
            return None
        return rsp.photosets[0].photoset

    def getPhotosetInfo(self, pid, method):
        """Returns a string containing information about a photoset (in XML)"""
        rsp = method(api_key=self.__flickrAPIKey, auth_token=self.token,
                     photoset_id=pid)
        if self.__testFailure(rsp):
            return None
        doc = libxml2.parseDoc(rsp.xml)
        info = str(doc.xpathEval( "/rsp/photoset")[0])
        doc.freeDoc()
        return info

    def getPhotoMetadata(self, pid):
        """Returns a string containing the photo metadata (in XML)"""
        rsp = self.fapi.photos_getInfo(api_key=self.__flickrAPIKey, auth_token=self.token,
                                       photo_id=pid)
        if self.__testFailure(rsp):
            return None
        doc = libxml2.parseDoc(rsp.xml)
        metadata = str(doc.xpathEval( "/rsp/photo")[0])
        doc.freeDoc()
        return  [ metadata, rsp.photo[0]['originalformat'] ]

    def getPhotoSizes(self, pid):
        """Returns an XMLNode which is a list of available sizes for a photo"""
        rsp = self.fapi.photos_getSizes(api_key=self.__flickrAPIKey, auth_token=self.token,
                                        photo_id=pid)
        if self.__testFailure(rsp):
            return None
        return rsp

    def getOriginalPhoto(self, pid):
        """Returns a URL which is the original photo, if it exists"""
        source = None
        rsp = self.getPhotoSizes(pid)
        if rsp == None:
            return None
        for s in rsp.sizes[0].size:
            if s['label'] == 'Original':
                source = s['source']
        return source

    def __downloadReportHook(self, count, blockSize, totalSize):
        """Invokes hook with the percentage of download completed."""
        if not self.__downloadHook:
            return
        p = 100 * count * blockSize / totalSize
        self.__downloadHook(min(p,100))

    def downloadURL(self, url, filename, hook = None):
        """Saves a photo in a file.
        If a hook function is specified, it will be regularly called
        during the download with an integer parameter indicating the
        percentage of the download accomplished."""
        self.__downloadHook = hook
        if hook:
            reporthook = self.__downloadReportHook
        else:
            reporthook = None
        urllib.urlretrieve(url, filename, reporthook)

def usage():
    """Command line interface usage"""
    print "Usage: Offlickr.py -i <flickr Id>"
    print "Backs up Flickr photos and metadata"
    print "Options:"
    print "\t-f <date>\tbeginning of the date range"
    print "\t\t\t(default: since you started using Flickr)"
    print "\t-t <date>\tend of the date range"
    print "\t\t\t(default: until now)"
    print "\t-d <dir>\tdirectory for saving files (default: ./dst)"
    print "\t-p\t\tback up photos in addition to photo metadata"
    print "\t-s\t\tback up all photosets (time range is ignored)"
    print "\t-b <browser>\tbrowser to use for authentication (default: opera)"
    print "\t-h\t\tthis help message"
    print "\nDates are specified in seconds since the Epoch (00:00:00 UTC, January 1, 1970)."
    print "\nVersion " + __version__

def fileWrite(filename, string):
    """Write a string into a file"""
    f = open(filename, 'w')
    f.write(string)
    f.close()
    print "Written as", filename

def downloadHook(p):
    print "\r %3d %%" % p,
    sys.stdout.flush()

def backupPhotos(offlickr, target, dateLo, dateHi, getPhotos):
    """Back photos up for a particular time range"""
    if dateHi == maxTime:
        t = time.time()
        print "For incremental backups, the current time is %.0f" % t
        print "You can rerun the program with '-f %.0f'" % t

    photos = offlickr.getPhotoList(dateLo, dateHi)
    if photos == None:
        print "No photos found"
        sys.exit(1)

    total = len(photos)
    print "Backing up" , total , "photos"

    i = 0
    for p in photos:
        i = i + 1
        pid = str(int(p['id'])) # Making sure we don't have weird things here
        print str(i) + "/" + str(total) + ": " + pid + ": " + p['title']
        # Get Metadata
        metadata = offlickr.getPhotoMetadata(pid)
        if metadata == None:
            print "Failed!"
            continue
        fileWrite(target + '/' + pid + '.xml', metadata[0])
        # Do we want the picture too?
        if getPhotos == False:
            continue
        f = pid + '.' + metadata[1]
        source = offlickr.getOriginalPhoto(pid)
        if source == None:
            print "Oopsie, no photo found"
        print 'Retrieving ' + source + ' as ' + f
        offlickr.downloadURL(source, target + '/' + f, downloadHook)
        print "\r... done!"

def backupPhotosets(offlickr, target):
    """Back photosets up"""
    photosets = offlickr.getPhotosetList()
    if photosets == None:
        print "No photosets found"
        sys.exit(0)

    total = len(photosets)
    print "Backing up" , total , "photosets"

    i = 0
    for p in photosets:
        i = i + 1
        pid = str(int(p['id'])) # Making sure we don't have weird things here
        print str(i) + "/" + str(total) + ": " + pid + ": " + p.title[0].elementText
        # Get Metadata
        info = offlickr.getPhotosetInfo(pid, offlickr.fapi.photosets_getInfo)
        if info == None:
            print "Failed!"
        else:
            fileWrite(target + '/set_' + pid + '_info.xml', info)
        photos = offlickr.getPhotosetInfo(pid, offlickr.fapi.photosets_getPhotos)
        if photos == None:
            print "Failed!"
        else:
            fileWrite(target + '/set_' + pid + '_photos.xml', photos)
        # Do we want the picture too?

def main():
    """Command-line interface"""
    # Default options
    flickrUserId = None
    dateLo = '1'
    dateHi = maxTime
    getPhotos = False
    target = 'dst'
    browser = 'opera'
    photosets = False

    # Parse command line
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hpsb:f:t:d:i:", ["help"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
            sys.exit(0)
        if o == '-i':
            flickrUserId = a
        if o == '-p':
            getPhotos = True
        if o == '-f':
            dateLo = a
        if o == '-t':
            dateHi = a
        if o == '-d':
            target = a
        if o == '-b':
            browser = a
        if o == '-s':
            photosets = True

    # Check that we have a user id specified
    if flickrUserId == None:
        print "You need to specify a Flickr Id"
        sys.exit(1)

    # Check that the target directory exists
    if not os.path.isdir(target):
        print target + " is not a directory; please fix that."
        sys.exit(1)

    offlickr = Offlickr(flickrAPIKey, flickrSecret, flickrUserId, browser)

    if photosets == False:
        backupPhotos(offlickr, target, dateLo, dateHi, getPhotos)
    else:
        backupPhotosets(offlickr, target)

if __name__ == "__main__":
    main()
