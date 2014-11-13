#!/usr/bin/python3
import praw
import requests
import re
import sys
import time
import datetime
from subprocess import check_output
import platform
import os.path
import random

USERNAME            = ""
PASSWORD            = ""
SUBREDDIT           = ""
IMAGENAME           = "CurrentModRec.png"
USER_AGENT          = "CycleModRecs 1.0 by /u/boib"
CYCLE_FREQ_MINUTES  = 2
BLURB_TAG           = "#####"
BANNER_TAG          = "####"
MODRECPOOL          = "modrecpool"
CURRENT_BOOK_FILE   = ""
DAILY_BANNER_FILE   = "daily-banner-list"

logBuf = ""
logTimeStamp = ""
fakeit = False
DEBUG = None

#################################################
def setDebug (d):
    global DEBUG
    DEBUG = d

#################################################
def debugFunc(s, start=False, stop=False):

    global logBuf
    global logTimeStamp

    print (s)

    logBuf = logBuf + s + "\n\n"
    if stop:
        r.submit("bookbotlog", logTimeStamp, text=logBuf)
        logBuf = ""

    #
    # p = r.submit("bookbotlog", "Post from PRAW", text="TESTING")
    # p.permalink is url of post
    # p.add_comment("praw is pwar")
    # thing = r.get_submission(url=p.permalink)
    # thing.add_comment("thing from get_submission")
    #


    #   import datetime
    #   today = datetime.date.today()
    #   print today.strftime('We are the %d, %b %Y')

    # import time
    #   time.strftime("%H:%M:%S %d%b%Y") - 16:19:41 24Jul2014
#################################################


def init ():
    r = praw.Reddit(user_agent=USER_AGENT)
    # so that reddit wont translate '>' into '&gt;'
    r.config.decode_html_entities = True
    return r
#################################################


def login (r, username, password):
    Trying = True
    while Trying:
        try:
            r.login(username, password)
            print('Successfully logged in')
            Trying = False
        except praw.errors.InvalidUserPass:
            print('Wrong Username or Password')
            quit()
        except Exception as e:
            print("%s" % e)
            time.sleep(5)
#################################################



def decodeBook(str):
    """ Takes a string and decodes the book format fields and returns a dict. """
    book = {"author":"", "moderator":"", "imageurl": "", "blurb": "", "title":""}

    formatstrs = ['author', 'moderator', 'imageurl', 'blurb']

    # 'imagefile' is a requirement, dont proceed if it's not there
    if re.search('{imageurl}', str, re.I):
        bookarray = str.splitlines()

        # '{book}' was stripped out in .split({book}), it's always the 1st line
        book['title'] = bookarray[0]
        if len(book['title']) == 0 or len(book['title']) > 150:
            DEBUG("decodeBook: decode error - title too long or too short" + book['title'])
        else:
            for x in bookarray:

                # ensure there are alpha chars in this string
                if re.search('[a-zA-Z]', x):
                    for s in formatstrs:
                        searchstr = "{%s}(.*)" % s
                        m = re.search(searchstr, x, re.I)
                        if m:
                            book[s] = m.group(1).strip()
                            break

    if not book['title'] or not book['imageurl']:
        DEBUG("decodeBook: missing title (%s) or imageurl (%s)" % (book['title'], book['imageurl']))
        book = {}
#    print (book)
    return book
#################################################
#def verifyImageUploaded (sr, name):
#    """ verify the image file exists on the stylesheet page """
#
#    DEBUG("verifyImageUploaded: Looking for (%s)" % name)
#    imgs = sr.get_stylesheet()['images']
#    for i in imgs:
#        if name == i['name']:
#            DEBUG("verifyImageUploaded: found it %s" % i['url'])
#            return True
#
#    DEBUG("verifyImageUploaded: %s not found" % name)
#    return False
#
#
#################################################



def updateBookImageName (sr, imagefile):
    """ update the stylesheet with the image file name.
        even if the imagename is already what we want, we still
        call set_stylesheet() because reddit requires that when
        uploading an image with the same name.
     """

    global fakeit

    if imagefile.endswith(".png"):
        imagefile = imagefile[:-4]
    sheet = sr.get_stylesheet()['stylesheet']
    newsheet = sheet
#OLD    m = re.search("\/\*change the sidebar pic\*\/\s*(\.side\s*{.*?})", sheet, re.I|re.DOTALL)

    m = re.search("(\.titlebox\s*.*?background:\s*url\(%%.*?%%\).*?})", sheet, re.I|re.DOTALL)

    if m:
#OLD        newside = re.sub(r'background-image:\s*url\(%%.*%%\);',
#OLD                         r'background-image: url(%%' + imagefile + r'%%);',
#OLD                         m.group(1))

        newside = re.sub(r'background:\s*url\(%%.*%%\)', r'background: url(%%' + imagefile + r'%%)', m.group(1))


        #DEBUG("updateBookImageName: side=%s" % m.group(1))
        #DEBUG("updateBookImageName: newside=%s" % newside)
        if newside == m.group(1):
            DEBUG("updateBookImage: imagename has not changed")
        else:
            DEBUG("updateBookImage: imagename HAS changed")
            newsheet = sheet.replace(m.group(1), newside)

            # a little sanity check - newsheet should be about the same size as sheet
            if abs(len(sheet)-len(newsheet)) > 20:
                DEBUG("updateBookImage: size diff (%s) of sheet-newsheet is too much" % abs(sheet-newsheet), stop=True)
                # todo - write sheet and newsheet to file
                quit()

        if not fakeit:
            e = sr.set_stylesheet(newsheet)
            if e['errors']:
                DEBUG("updateBookImageName: error from set_stylesheet() (%s)" % e['errors'], stop=True)
                quit()
#################################################



def updateBlurb(sr, blurb, banner):
    """ update the book blurb on the sidebar page """

    global fakeit

    if not blurb:
        blurb = ' '

    if not banner:
        banner = ''

    DEBUG("updateBlurb: blurb (%s)" % blurb)
    DEBUG("updateBlurb: banner (%s)" % banner)

    sb = sr.get_settings()["description"]
    m = re.search(BLURB_TAG + "(.*)", sb)
    if not m:
        DEBUG("updateBlurb: Error finding (%s) in sidebar" % BLURB_TAG, stop=True)
        quit()

    if len(m.group(1)) < 2 and len(blurb) < 2:
        DEBUG("updateBlurb: No blurb in old or new.  Not updating.");
    else:
        blurb = '[](' + blurb + ')'
        newblurb = BLURB_TAG + blurb
        newsb = re.sub(BLURB_TAG + '(.*)', newblurb, sb)


        # update banner
        m = re.search(BANNER_TAG + "([^#].*)", newsb)
        if not m:
            DEBUG("updateBanner: Error finding (%s) in sidebar" % BANNER_TAG)
        elif len(m.group(1)) < 2 or len(banner) < 5:
            DEBUG("updateBanner: No banner in old or new.  Not updating.");
        else:
            newbanner = BANNER_TAG + banner
            newsb = re.sub(BANNER_TAG + '(.*)', newbanner, newsb, count=1)

            if not fakeit:
                e = sr.update_settings(description = newsb)
                if e['errors']:
                    DEBUG("updateBlurb: error from update_settings() (%s) " % e['errors'], stop=True)
                    quit()


#################################################




def updateCurrentBookTitle(index):
    """ update the current book title tag on the modrecpool page """

    global fakeit

    if not fakeit:
        f = open(CURRENT_BOOK_FILE, "w")
        f.write(str(index) + "\n")
        f.close()
#    newcontent = ''
#    newcontent = re.sub("{CurrentBookTitle}(.*)", "{CurrentBookTitle} " + title, content)
#    if newcontent:
#        if newcontent != content:
#            DEBUG("updateCurrentBookTitle: Calling edit_wiki_page()")
#            e = sr.edit_wiki_page(MODRECPOOL, newcontent)
#            if e:
#                DEBUG("updateCurrentBookTitle: edit_wiki_page error (%s)" % e)
#
#        else:
#            DEBUG("updateCurrentBookTitle: new content is same as old content")
#
#    else:
#        DEBUG("updateCurrentBookTitle: no new content")
#################################################



def downloadImage(imageUrl, localFileName):

    DEBUG("downloadImage: Looking for %s" % imageUrl)
    IDENTIFY = 'identify'
    CONVERT = 'convert'

    if platform.system() == 'Windows':
        IDENTIFY = 'C:/Program Files/ImageMagick-6.8.9-Q16/identify.exe'
        CONVERT = 'C:/Program Files/ImageMagick-6.8.9-Q16/convert.exe'


    ext = os.path.splitext(imageUrl)[1][1:].strip()
    if not ext:
        imageUrl = imageUrl + ".png"

    response = requests.get(imageUrl)

    if response.status_code == 200:
        print('Downloading %s...' % (localFileName))

        with open(localFileName, 'wb') as fo:
            for chunk in response.iter_content(4096):
                fo.write(chunk)

        response.connection.close()
        try:
            output = check_output([IDENTIFY, localFileName])
            a = output.split()
            DEBUG("downloadImage: image is (%s) (%s)" % (a[1].decode("utf-8"), a[2].decode("utf-8")))
            if a[2] != b"163x260":
                o = check_output([CONVERT,  localFileName, "-resize", "163x260!", localFileName])
                DEBUG("(%s) image converted to 163x260" % imageUrl)
            elif a[1] != b"PNG":
                o = check_output(["convert",  localFileName, localFileName])
                DEBUG("(%s) image converted to PNG" % imageUrl)
        except Exception as e:
            DEBUG('downloadImage: Error in IDENTIFY or CONVERT %s' % e)
            return False

        return True
    else:
        DEBUG("downloadImage: Error(%s) finding (%s)" % (response.status_code, imageUrl))
        response.connection.close()
        return False


#################################################

def uploadImage (sr, filename):
    """   """
    global fakeit

    if not fakeit:
        DEBUG("uploadImage: (%s)" % filename)
        sr.upload_image(filename)

    return
##############################################################################

def getBanner (sr):

    banner = ""

    if not os.path.isfile(DAILY_BANNER_FILE):
        wp = sr.get_wiki_page("relatedsubreddits")
        raw = wp.content_md.split("\n")

        myList = []
        for x in raw:
            if re.search("^###[^#]", x):
                x = re.sub("\*", "", x)
                myList.append(x[3:].strip())

        if len(myList) < 10:
            return ""

        random.shuffle(myList)

        f = open(DAILY_BANNER_FILE, 'w')
        f.write("\n".join(myList))
        f.close()

    # read file, remove 1st item, write new file
    try:
        f = open(DAILY_BANNER_FILE)
        myList = f.readlines()
        f.close()
    except:
        pass

    try:
        banner = myList.pop(0).strip()
        if len(myList) == 0:
            os.remove(DAILY_BANNER_FILE)
        else:
            f = open(DAILY_BANNER_FILE, 'w')
            f.write("".join(myList))
            f.close()
    except:
        pass

    if banner:
        banner = "===== Today's Book Related Subreddit: **%s** =====" % banner
    return banner



def checkForAMA (r):

#    ama at 2pm 2014-08-15
#
#    if any amas for TODAY
#        upload image and blurb
#
#    else if any amas for tomorrow
#        upload image and blurb
#
#    else
#        do normal cycle


    month = []
    year = []
    day = []

    # today's date
    month.append(int(datetime.datetime.now().strftime("%m")))
    year.append(int(datetime.datetime.now().strftime("%Y")))
    day.append(int(datetime.datetime.now().strftime("%d")))

    # tomorrow's date
    month.append(int((datetime.date.today() + datetime.timedelta(days=1)).strftime("%m")))
    year.append (int((datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y")))
    day.append  (int((datetime.date.today() + datetime.timedelta(days=1)).strftime("%d")))


    # filename: 2014-08-15-Sonya Cobb

    #
    # get dir list
    # if sched with todays date
    # elif if sched with tomorrows date
    # else return False
    #

    schedDir = os.listdir("sched/")

    for i in range(2):

        imageurl = ""
        blurburl = ""
        banner = ""
        for sf in schedDir:

            if re.search("%d-%02d-%02d" % (year[i], month[i], day[i]), sf):
                DEBUG("checkForAMA: Found (%s)" % sf)
                # read this file contents
                # imageurl =
                # blurburl =
                # if fail, return False
                f = open("sched/" + sf, 'r')
                buf = f.readlines()
                f.close()

                for b in buf:
                    if b[0] == '#' or len(b) < 5:
                        continue

                    if b.startswith('imageurl:'):
                        imageurl = b[len('imageurl:'):].strip()

                    if b.startswith('blurburl:'):
                        blurburl = b[len('blurburl:'):].strip()

                    if b.startswith('banner:'):
                        banner = b[len('banner:'):].strip()


                DEBUG("checkForAMA: (%s) (%s) (%s)" % (sf, imageurl, blurburl))
                break # out of sf in schedDir

        if imageurl and blurburl:
            break # out of for range

    if not imageurl or not blurburl:
        DEBUG("checkForAMA: Found nothing")
        return False

    DEBUG("checkForAMA: Doing this: (%s) (%s) (%s) (%s)" % (sf, imageurl, blurburl, banner))

    ok = downloadImage(imageurl, IMAGENAME)
    if not ok:
        # image url is no good, abort
        DEBUG()
        return False


    sr = r.get_subreddit(SUBREDDIT)

    #
    # upload the image to the stylesheet page
    #
    uploadImage(sr, IMAGENAME)

    #
    # update stylesheet with imagefile name
    #
    updateBookImageName(sr, IMAGENAME)

    #
    # update blurb in sidebar
    #
    updateBlurb(sr, blurburl, banner)

    return True





###############################################################################
def cycleBooks (r):

    nextBook = 0
    #
    # get the "modrecpool" wiki page
    #
    sr = r.get_subreddit(SUBREDDIT)
    mrp = sr.get_wiki_page(MODRECPOOL)


    try:
        f = open(CURRENT_BOOK_FILE, "r")
        nextBook = int(f.readline()) + 1
        f.close()
    except:
        nextBook = 0;


    DEBUG("cycleBooks: next book index = %d" % nextBook)

    #
    # get the list of mod rec books
    #
    mrps = mrp.content_md.split("{Book}")
    bookList = []
    for i in mrps:
        i = i.strip()

        if len(i) < 10:
            continue

        myBook = decodeBook(i)
        if myBook:
            bookList.append(myBook)


    numBooks = len(bookList)
    DEBUG("found %s books" % numBooks)
    if len(bookList) < 2:
        DEBUG("Not enough books", stop=True)
        quit()

    # if we're at the end, start over from top
    if nextBook >= numBooks:
        nextBook = 0;

    DEBUG("\nfound current book **%s** at index:%s out of %s" % (bookList[nextBook]['title'], nextBook, numBooks))

    #
    # verify image file URL is valid
    #
    count = len(bookList)
    ok = False
    while not ok and count > 0:
        ok = downloadImage(bookList[nextBook]['imageurl'], IMAGENAME)
        if not ok:
            nextBook += 1
            count -= 1

    if count == 0:
        DEBUG("ERROR: CANNOT FIND A SINGLE BOOK IMAGE", stop=True)
        quit

    #
    # get today's banner
    #
    banner = getBanner(sr)

    #
    # upload the image to the stylesheet page
    #
    uploadImage(sr, IMAGENAME)

    #
    # update stylesheet with imagefile name
    #
    updateBookImageName(sr, IMAGENAME)

    #
    # update blurb in sidebar
    #
    updateBlurb(sr, bookList[nextBook]['blurb'], banner)


    #
    # save the current book index
    #
    updateCurrentBookTitle(nextBook)
#########################################################################


if __name__=='__main__':
    #
    # init and log into reddit
    #


    if len(sys.argv) > 1:
        if sys.argv[1] == "fakeit":
            fakeit = True
        else:
            print ("\n\n CycleModRecs <fakeit>")
            quit()

    setDebug (debugFunc)

    f = open('cmr.dat', 'r')
    buf = f.readlines()
    f.close()

    for b in buf:
        if b[0] == '#' or len(b) < 5:
            continue

        if b.startswith('username:'):
            USERNAME = b[len('username:'):].strip()

        if b.startswith('password:'):
            PASSWORD = b[len('password:'):].strip()

        if b.startswith('subreddit:'):
            SUBREDDIT = b[len('subreddit:'):].strip()


    if not USERNAME or not PASSWORD or not SUBREDDIT:
        DEBUG('cmd: Missing username, password or subreddit')
        quit()


    CURRENT_BOOK_FILE   = "CrntBookIndx-" + SUBREDDIT + ".txt"

    r = init()
    login(r, USERNAME, PASSWORD)


    if platform.system() == 'Windows':
        formatstr = "%d%b%Y-%H:%M:%S"
    else:
        formatstr = "%d%b%Y-%H:%M:%S %Z"

    logTimeStamp = "CMR - /r/" + SUBREDDIT + " - " + time.strftime(formatstr) + (" TrialRun" if fakeit else "")

    try:
        if not checkForAMA(r):
            cycleBooks(r)

    except Exception as e:
        DEBUG('An error has occured: %s' % e)
        #quit()

    DEBUG("", stop=True)

#    print('Running again in ' + str(CYCLE_FREQ_MINUTES) + ' minutes.\n')
#    time.sleep(30)
    #time.sleep(CYCLE_FREQ_MINUTES*60)




