#!/usr/bin/env python

# Generate spritesheets and css for linking scrolls in /r/scrolls
#
# Thx to scrollsguide for the API !
# usage : python updatescrolls.py reddit_user reddit_pass subreddit
#
#

import urllib
import urllib2
import cStringIO
import json
import sys
import Image
import math
import string
import praw
import os
import time
import htmlentity2ascii

if len(sys.argv) < 4:
    print("Usage : %s reddit_user reddit_pass subreddit" % sys.argv[0])
    sys.exit(11)

base_api = "http://a.scrollsguide.com/"
user = sys.argv[1]
password = sys.argv[2]
subr_name = sys.argv[3]
spritesheetname = "spritesheet"
type_img = "jpg"


def getUrl(url):
    # google chrome user agent

    use_chrome_useragent = True
    if use_chrome_useragent:
        request = urllib2.Request(url)
        request.add_header("User-Agent", "Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36")
        f = urllib2.urlopen(request)
    else:
        f = urllib.urlopen(url)

    data = f.read()
    f.close()
    return data


def newImg(x, y):
    img = Image.new(
        mode='RGBA',
        size=(x, y),
        color=(0, 0, 0))
    return img


def get_all_scrolls(limit=0):  # limit number of dl for debug and being nice with the bandwidth of kbasten
    print("== Getting raw scrolls data...")
    scrolls = []

    sgapi_scrolls = json.loads(getUrl(base_api+"scrolls"))
    if sgapi_scrolls['msg'] == 'fail':  # error API request
        sys.exit(11)
    sg_scrolls = sgapi_scrolls['data']
    for scroll in sg_scrolls:
        if (limit != 0) and (len(scrolls) >= limit):
            return scrolls
        img_url = '%simage/screen?%s&size=small' % (base_api, urllib.urlencode({'name': scroll['name']}))  # img api url
        scrolls.append({"name": scroll['name'], "img_url": img_url, "id": scroll['id']})  # only get the usefull data
    print("Done!")
    return scrolls


def download_images(scrolls):  # store all image in list
    print("== Getting all images...\nStarting..")
    nb_sc = len(scrolls)
    i = 1
    for scroll in scrolls:
        done = False
        while not done:
            try: 
                scroll['image'] = Image.open(cStringIO.StringIO(getUrl(scroll['img_url'])))
                done = True
            except IOError:
                print(scroll['img_url'])
                print("Rate limit exceeded - sleeping for 5s and trying again")
                print("------------------------------------------------------")
                time.sleep(5)
        print("%d/%d %s" % (i, nb_sc, scroll['name']))
        i += 1
    print("Done! got %s images\nStarting spritesheet" % len(scrolls))


def upload_spritesheets(nb_spritesheets, spritesheetname, type_img):
    print ("Starting spritesheet upload...\nConnecting to reddit")
    r = praw.Reddit(user_agent='img css uploader [praw]')
    r.login(user, password)
    subreddit = r.get_subreddit(subr_name)
    print("Connected!\nUploading images...")
    for i in xrange(0, nb_spritesheets+1):
        filename = "%s-%d.%s" % (spritesheetname, i, type_img)
        print("uploading " + filename)
        subreddit.upload_image(filename, "%s-%d" % (spritesheetname, i))
        os.remove(filename)
    print("All done!")


def update_css(css):
    print ("Starting update css...\nConnecting to reddit")
    splitkey = "/**botcss**/"
    r = praw.Reddit(user_agent='css updater [praw]')
    r.login(user, password)
    print("Connected!\nUpdating css...")
    subreddit = r.get_subreddit(subr_name)

    # wtf T_T why htmlentity2ascii ? idk bug without...
    cur_css = htmlentity2ascii.convert(subreddit.get_stylesheet()['stylesheet'].split(splitkey, 1)[0])
    newcss = '%s\n%s\n%s\n' % (cur_css, splitkey, css)
    subreddit.set_stylesheet(newcss)
    print ('Done!')


def gen_css(spritesheetname, scrolls):
    statichover = "font-size: 0em; height: 375px; width: 210px; z-index: 6;"
    staticafter = " margin-left: 1px;  font-size: 0.6em; color: rgb(255,137,0);"
    staticallrules = "{display: inline-block; cursor:default; clear: both; padding-top:5px; margin-right: 2px;}"
    css, all_css = "", "\n"
    for scroll in scrolls:
        sprite_name = "%s-%d" % (spritesheetname, scroll['sprite_id'])
        name = string.lower(scroll['name']).replace(" ", "")
        all_css += ".content a[href=\"#" + name + "\"], "  # css rules for all scrolls
        css += (".content a[href=\"#" + name + "\"]:hover {" + statichover + " background-image: url(%%" + sprite_name + "%%);  background-position: -"+str(scroll['pos'][0])+"px -" + str(scroll['pos'][1]) + "px; }\n")
        css += (".content a[href=\"#" + name + "\"]::after {" + staticafter + " content: \"[" + scroll['name'] + "]\";}\n")
    all_css = all_css[:-2] + staticallrules
    css += all_css
    return css


def spritesheeter(scrolls):
    nb_per_sheet, quality_jpeg = 20, 90
    loc_y, loc_x, i, img_process, cur_spritesheet = 0, 0, 0, 0, 0
    download_images(scrolls)
    image_w, image_h = scrolls[0]['image'].size
    perline = (int)(round(math.sqrt(nb_per_sheet)))  # 'perfect size' spritesheet
    master_w = image_w * perline
    master_h = image_h * perline
    spritesheet = newImg(master_w, master_h)
    for scroll in scrolls:
        spritesheet.paste(scroll['image'], (loc_x, loc_y))  # paste image in spritesheet
        scroll['sprite_id'], scroll['pos'] = cur_spritesheet, (loc_x, loc_y)  # store data for css rules
        loc_x += image_w
        i += 1
        if i == perline:
            loc_x, i = 0, 0
            loc_y += image_h
        img_process += 1
        if img_process == (perline*perline):  # change of spritesheet to avoid big files
            print ("Want save %d spritesheet" % cur_spritesheet)
            spritesheet.save("%s-%d.%s" % (spritesheetname, cur_spritesheet, type_img), quality=quality_jpeg)  # save file
            spritesheet = newImg(master_w, master_h)
            loc_y, loc_x, img_process = 0, 0, 0  # reset everything
            cur_spritesheet += 1
            print ("Saved! Continue..")
    print("Last spritesheet...")
    spritesheet.save("%s-%d.%s" % (spritesheetname, cur_spritesheet, type_img), quality=quality_jpeg)  # save the scrolls left
    print("All done ! Gen css")
    return cur_spritesheet


def main():
    scrolls = get_all_scrolls()
    nb_spritesheet = spritesheeter(scrolls)
    upload_spritesheets(nb_spritesheet, spritesheetname, type_img)
    css = gen_css(spritesheetname, scrolls)
    update_css(css)

if __name__ == '__main__':
    main()
