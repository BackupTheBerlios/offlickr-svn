# Offlickr
# Hugo Haas -- mailto:hugo@larve.net -- http://larve.net/people/hugo/
# Homepage: http://larve.net/people/hugo/2005/12/offlickr/
# License: GPLv2
#
# wget patch by Daniel Drucker <dmd@3e.org>

import sys
import libxml2
import urllib
import getopt
import time
import os.path
import threading

# Beej's Python Flickr API
# http://beej.us/flickr/flickrapi/
from flickrapi import FlickrAPI

__version__ = '0.6 - 2007-05-20'
maxTime = '9999999999'

# Gotten from Flickr
flickrAPIKey = '1391fcd0a9780b247cd6a101272acf71'
flickrSecret = 'fd221d0336de3b6d'

class Offlickr:

    def __init__(self, key, secret, uid, httplib = None, browser = "lynx",
		 verbose = False):
        """Instantiates an Offlickr object
        An API key is needed, as well as an API secret and a user id.
        A browser can be specified to be used for authorizing the program
        to access the user account."""
        self.__flickrAPIKey = key
        self.__flickrSecret = secret
	self.__httplib = httplib
        # Get authentication token
        self.fapi = FlickrAPI(self.__flickrAPIKey, self.__flickrSecret)
        self.token = self.fapi.getToken(browser=browser)
        self.flickrUserId = uid
	self.verbose = verbose

    def __testFailure(self, rsp):
        """Returns whether the previous call was successful"""
        if rsp['stat'] == "fail":
            print "Error!"
            return True
        else:
            return False

    def getPhotoList(self, dateLo, dateHi):
        """Returns a list of photo given a time frame"""
        n = 0
	flickr_max = 500
        photos = [ ]

	print "Retrieving list of photos"
        while True:
	    if self.verbose:
		print "Requesting a page..."
            n = n + 1
            rsp = self.fapi.photos_search(api_key=self.__flickrAPIKey, auth_token=self.token,
                                          user_id = self.flickrUserId,
                                          per_page = str(flickr_max), # Max allowed by Flickr
                                          page = str(n),
                                          min_upload_date = dateLo, max_upload_date = dateHi)
            if self.__testFailure(rsp):
                return None
            if rsp.photos[0]['total'] == '0':
                return None
            photos += rsp.photos[0].photo
	    if self.verbose:
		print " %d photos so far" % len(photos)
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
        """Returns an array containing containing the photo metadata (as a string), and the format of the photo"""
	if self.verbose:
	    print "Requesting metadata for photo %s" % pid
        rsp = self.fapi.photos_getInfo(api_key=self.__flickrAPIKey, auth_token=self.token,
                                       photo_id=pid)
        if self.__testFailure(rsp):
            return None
        doc = libxml2.parseDoc(rsp.xml)
        metadata = doc.xpathEval("/rsp/photo")[0].serialize()
        doc.freeDoc()
        return  [ metadata, rsp.photo[0]['originalformat'] ]

    def getPhotoComments(self, pid):
        """Returns an XML string containing the photo comments"""
	if self.verbose:
	    print "Requesting comments for photo %s" % pid
        rsp = self.fapi.photos_comments_getList(api_key=self.__flickrAPIKey,
						auth_token=self.token,
						photo_id=pid)
        if self.__testFailure(rsp):
            return None
        doc = libxml2.parseDoc(rsp.xml)
        comments = doc.xpathEval( "/rsp/comments")[0].serialize()
        doc.freeDoc()
        return comments

    def getPhotoSizes(self, pid):
        """Returns a string with is a list of available sizes for a photo"""
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
        if self.__verbose == False:
            return
        p = 100 * count * blockSize / totalSize
        if (p > 100):
            p = 100
        print "\r %3d %%" % p,
        sys.stdout.flush()

    def downloadURL(self, url, target, filename, verbose = False):
        """Saves a photo in a file"""
        self.__verbose = verbose
	tmpfile = "%s/%s.TMP" % (target, filename)
	if self.__httplib == 'wget':
	    cmd = 'wget -q -t 0 -T 120 -w 10 -c -O %s %s' % (tmpfile, url)
	    os.system(cmd)
	else:
	    urllib.urlretrieve(url, tmpfile,
			       reporthook=self.__downloadReportHook)
	os.rename(tmpfile, "%s/%s" % (target, filename))

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
    print "\t-n\t\tdo not redownload anything which has already been downloaded (only jpg checked)"
    print "\t-o\t\toverwrite photo, even if it already exists"
    print "\t-s\t\tback up all photosets (time range is ignored)"
    print "\t-w\t\tuse wget instead of internal Python HTTP library"
    print "\t-c <threads>\tnumber of threads to run to backup photos (default: 1)"
    print "\t-b <browser>\tbrowser to use for authentication (default: opera)"
    print "\t-v\t\tverbose output"
    print "\t-h\t\tthis help message"
    print "\nDates are specified in seconds since the Epoch (00:00:00 UTC, January 1, 1970)."
    print "\nVersion " + __version__

def fileWrite(filename, string):
    """Write a string into a file"""
    f = open(filename, 'w')
    f.write(string)
    f.close()
    print "Written as", filename

class photoBackupThread(threading.Thread):
   def __init__ (self, sem, i, total, id, title, offlickr, target, getPhotos,
		 doNotRedownload, overwritePhotos):
       self.sem = sem
       self.i = i
       self.total = total
       self.id = id
       self.title = title
       self.offlickr = offlickr
       self.target = target
       self.getPhotos = getPhotos
       self.doNotRedownload = doNotRedownload
       self.overwritePhotos = overwritePhotos
       threading.Thread.__init__(self)

   def run(self):
       backupPhoto(self.i, self.total, self.id, self.title, self.target, self.offlickr, self.doNotRedownload, self.getPhotos, self.overwritePhotos)
       self.sem.release()

def backupPhoto(i, total, id, title, target, offlickr, doNotRedownload, getPhotos, overwritePhotos):
    print str(i) + "/" + str(total) + ": " + id + ": " + title.encode("utf-8")
    if doNotRedownload and os.path.isfile(target + '/' + id + '.xml') and os.path.isfile(target + '/' + id + '-comments.xml') and ((not getPhotos) or (getPhotos and os.path.isfile(target + '/' + id + '.jpg'))):
	print "Photo %s already downloaded; continuing" % id
	return
    # Get Metadata
    metadataResults = offlickr.getPhotoMetadata(id)
    if metadataResults == None:
	print "Failed!"
	sys.exit(2)
    metadata = metadataResults[0]
    format = metadataResults[1]
    # Write metadata
    fileWrite(target + '/' + id + '.xml', metadata)
    # Get comments
    photoComments = offlickr.getPhotoComments(id)
    fileWrite(target + '/' + id + '-comments.xml',
	      photoComments)
    # Do we want the picture too?
    if getPhotos == False:
	return
    filename = id + '.' + format
    source = offlickr.getOriginalPhoto(id)
    if source == None:
	print "Oopsie, no photo found"
	return
    if os.path.isfile("%s/%s" % (target, filename)) and not overwritePhotos:
	print "%s already downloaded... continuing" % filename
	return
    print 'Retrieving ' + source + ' as ' + filename
    offlickr.downloadURL(source, target, filename, verbose = True);
    print "Done downloading %s" % filename

def backupPhotos(threads, offlickr, target, dateLo, dateHi, getPhotos,
		 doNotRedownload, overwritePhotos):
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

    if threads > 1:
	concurrentThreads = threading.Semaphore(threads)
    i = 0
    for p in photos:
        i = i + 1
        pid = str(int(p['id'])) # Making sure we don't have weird things here
	if threads > 1:
	    concurrentThreads.acquire()
	    downloader = photoBackupThread(concurrentThreads, i, total, pid,
					   p['title'], offlickr,
					   target, getPhotos, doNotRedownload,
					   overwritePhotos)
	    downloader.start()
	else:
	    backupPhoto(i, total, pid, p['title'], target, offlickr, doNotRedownload, getPhotos, overwritePhotos)

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
    overwritePhotos = False
    doNotRedownload = False
    target = 'dst'
    browser = 'opera'
    photosets = False
    verbose = False
    threads = 1
    httplib = None

    # Parse command line
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hvponswb:f:t:d:i:c:", ["help"])
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
        if o == '-o':
            overwritePhotos = True
        if o == '-n':
            doNotRedownload = True
        if o == '-f':
            dateLo = a
        if o == '-t':
            dateHi = a
        if o == '-d':
            target = a
        if o == '-b':
            browser = a
	if o == '-w':
	    httplib = 'wget'
        if o == '-c':
            threads = int(a)
        if o == '-v':
            verbose = True

    # Check that we have a user id specified
    if flickrUserId == None:
        print "You need to specify a Flickr Id"
        sys.exit(1)

    # Check that the target directory exists
    if not os.path.isdir(target):
        print target + " is not a directory; please fix that."
        sys.exit(1)

    offlickr = Offlickr(flickrAPIKey, flickrSecret, flickrUserId,
			httplib, browser, verbose)

    if photosets == False:
        backupPhotos(threads, offlickr, target, dateLo, dateHi, getPhotos,
		     doNotRedownload, overwritePhotos)
    else:
        backupPhotosets(offlickr, target)

if __name__ == "__main__":
    main()
