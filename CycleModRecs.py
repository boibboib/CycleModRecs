#!/usr/bin/python3
import praw
import requests
import re
import sys
import time

USERNAME            = "xxxx"
PASSWORD            = "xxxx"
SUBREDDIT           = "xxxx"
IMAGENAME           = "CurrentModRec.png"
USER_AGENT          = "CycleModRecs 1.0 by /u/boib"
CYCLE_FREQ_MINUTES  = 2
BLURB_TAG           = "#####"
MODRECPOOL          = "modrecpool"
CURRENT_BOOK_FILE   = "CurrentBookIndex.txt"

logBuf = ""
logTimeStamp = ""
fakeit = False


#################################################
def DEBUG (s, start=False, stop=False):

    global logBuf
    global logTimeStamp

    print (s)

    logBuf = logBuf + s + "\n\n"
    if stop:
        r.submit("bookbotlog", logTimeStamp, text=logBuf)

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
            print('Successfully logged in\n')
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
        if len(book['title']) == 0 or len(book['title']) > 50:
            DEBUG("decodeBook: decode error")
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
    m = re.search("\/\*change the sidebar pic\*\/\s*(\.side\s*{.*?})", sheet, re.I|re.DOTALL)
    if m:
        newside = re.sub(r'background-image:\s*url\(%%.*%%\);',
                         r'background-image: url(%%' + imagefile + r'%%);',
                         m.group(1))

        #DEBUG("updateBookImageName: side=%s" % m.group(1))
        #DEBUG("updateBookImageName: newside=%s" % newside)
        if newside == m.group(1):
            DEBUG("updateBookImage: imagename has not changed")
        else:
            DEBUG("updateBookImage: imagename HAS changed")
            newsheet = sheet.replace(m.group(1), newside)

            # a little sanity check - newsheet should be about the same size as sheet
            if abs(len(sheet)-len(newsheet)) > 20:
                DEBUG("updateBookImage: size diff (%s) of sheet-newsheet is too much" % abs(sheet-newsheet))
                # todo - write sheet and newsheet to file
                quit()

        if not fakeit:
            e = sr.set_stylesheet(newsheet)
            if e['errors']:
                DEBUG("updateBookImageName: error from set_stylesheet() (%s)" % e['errors'])
                quit()
#################################################



def updateBlurb(sr, blurb):
    """ update the book blurb on the sidebar page """

    global fakeit

    if not blurb:
        blurb = ' '

    DEBUG("updateBlurb: blurb (%s)" % blurb)

    if len(blurb) > 420:
        blurb = blurb[:420]

    sb = sr.get_settings()["description"]
    m = re.search(BLURB_TAG + "(.*)", sb)
    if not m:
        DEBUG("updateBlurb: Error finding (%s) in sidebar" % BLURB_TAG)
        quit()

    if len(m.group(1)) < 2 and len(blurb) < 2:
        DEBUG("updateBlurb: No blurb in old or new.  Not updating.");
    else:
        newblurb = BLURB_TAG + blurb
        newsb = re.sub(BLURB_TAG + '(.*)', newblurb, sb)

        if not fakeit:
            e = sr.update_settings(description = newsb)
            if e['errors']:
                DEBUG("updateBlurb: error from update_settings() (%s) " % e['errors'])
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

    if not imageUrl.endswith(".png") and not imageUrl.endswith(".jpg"):
        imageUrl = imageUrl + ".png"

    response = requests.get(imageUrl)

    if response.status_code == 200:
        print('Downloading %s...' % (localFileName))

        with open(localFileName, 'wb') as fo:
            for chunk in response.iter_content(4096):
                fo.write(chunk)

        response.close()
        return True
    else:
        DEBUG("downloadImage: Error(%s) finding (%s)" % (response.status_code, imageUrl))
        response.close()
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
        myBook = decodeBook(i)
        if myBook:
            bookList.append(myBook)


    numBooks = len(bookList)
    DEBUG("found %s books" % numBooks)
    if len(bookList) < 2:
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
        DEBUG("ERROR: CANNOT FIND A SINGLE BOOK IMAGE")
        quit

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
    updateBlurb(sr, bookList[nextBook]['blurb'])


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

    logTimeStamp = "CycleModRecs - /r/" + SUBREDDIT + " - " + time.strftime("%d%B%Y-%H:%M:%S %Z") + (" TrialRun" if fakeit else "")
    r = init()
    login(r, USERNAME, PASSWORD)


    #while True:
    try:
        cycleBooks(r)
    except Exception as e:
        DEBUG('An error has occured: %s' % e)
        #quit()

    DEBUG("", stop=True)

    #    print('Running again in ' + str(CYCLE_FREQ_MINUTES) + ' minutes.\n')
    #    time.sleep(CYCLE_FREQ_MINUTES*60)


