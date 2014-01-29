#!/usr/bin/python
#
# murfiebot.py
#

import sys
import httplib
import json
import twitter
import time
import urllib
import ConfigParser

# load config
config = ConfigParser.RawConfigParser()
config.read('murfiebot.cfg')

UPDATE_FREQ = config.getint('system', 'update_frequency')
API_ENDPOINT = config.get('murfie', 'api_endpoint')
TWITTER_CONSUMER_KEY = config.get('twitter', 'consumer_key')
TWITTER_CONSUMER_SECRET = config.get('twitter', 'consumer_secret')
TWITTER_ACCESS_TOKEN_KEY = config.get('twitter', 'access_token_key')
TWITTER_ACCESS_TOKEN_SECRET = config.get('twitter', 'access_token_secret')

# connect to the API
API_CONNECTION = httplib.HTTPSConnection(API_ENDPOINT)
last_update = 60

# keep track of the last mention we responded to
settings = open("./settings", "r")
since_bookmark = int(settings.readline())

twitter_api = twitter.Api(
	consumer_key=TWITTER_CONSUMER_KEY,
	consumer_secret=TWITTER_CONSUMER_SECRET,
	access_token_key=TWITTER_ACCESS_TOKEN_KEY,
	access_token_secret=TWITTER_ACCESS_TOKEN_SECRET)


def daemon_mode():
	global last_update
	global UPDATE_FREQ
	
	while True:
	
		print "last update: %s" % last_update
	
		checkTwitter()
	
		print "waiting %d seconds to check for more updates" % UPDATE_FREQ
	
		last_update = last_update + 1
		time.sleep(UPDATE_FREQ)
		
		
def checkTwitter():

	global since_bookmark

	print "checking for new mentions after %d" % since_bookmark

	mentions = twitter_api.GetMentions(since_id=since_bookmark)

	print "%d mentions found" % len(mentions)

	if len(mentions) > 0:

		for mention in mentions:

			# don't talk to yourself
			if mention.user.screen_name != "murfiebot":
			
				quotations = extract_quotations(mention.text)
				print 'quotations: %s' % quotations
				
				hashtags = extract_hashtags(mention.text)
				print 'hastags: %s' % hashtags
				
				if quotations is not None:
					matching_albums = search_albums(quotations[0])
					if matching_albums is not None:
						message = '@%s I found %d albums that match \"%s\", including \"%s\" - https://www.murfie.com/search?search=%s' % (mention.user.screen_name, len(matching_albums), quotations[0], matching_albums[0]['album']['title'], urllib.quote_plus(quotations[0]))
					else:
						message = 'Sorry @%s, I couldn\'t find any albums matching \"%s\"' % (mention.user.screen_name, quotations[0])
						
					print message
					post_response(message, mention.id)
					
				if hashtags is not None:
					matching_albums = search_albums(hashtags[0][1:])
					if matching_albums is not None:
						message = '@%s, I found %d albums that match %s, including \"%s\" - https://www.murfie.com/search?search=%s' % (mention.user.screen_name, len(matching_albums), hashtags[0], matching_albums[0]['album']['title'], hashtags[0][1:])
					else:
						message = 'Sorry @%s, I couldn\'t find any albums matching %s' % (mention.user.screen_name, hashtags[0])
						
					print message
					post_response(message, mention.id)
					
				if quotations is None and hashtags is None:
					message = "Hi @%s, I find music on Murfie.com (use a hashtag or quotes so I know what to look for :)" % mention.user.screen_name
					print message
					post_response(message, mention.id)

			# update bookmark
			if mention.id > since_bookmark:
				since_bookmark = mention.id
				settings = open("./settings", "w")
				settings.write("%d" % since_bookmark)


def post_response(message, mention_id):
	try:
		twitter_api.PostUpdate(status=message, in_reply_to_status_id=mention_id)
	except Exception:
		print Exception


def extract_quotations(message):

	quotations = message.split('"')[1::2]
	
	if quotations is not None and len(quotations) > 0:
		return quotations
	else:
		return None
		
		
def extract_hashtags(message):
	if message.find('#') > 0:
		hashtags = []
		for tag in message.split('#'):

			tagend = tag.find(' ')
			
			if tagend > -1:
				hashtags.append('#' + tag[:tagend])
			else:
				hashtags.append('#' + tag)
			
		# drop the first "tag", it's bogus
		hashtags = hashtags[1:]
		
		return hashtags
	else:
		return None
		
		
def search_albums(search_string):

	# encode search string
	search_string = urllib.quote_plus(search_string)
	
	# construct request
	api_url = '/albums?q=%s' % search_string
	API_CONNECTION.request('GET', api_url)
	
	# execute request
	response = API_CONNECTION.getresponse()
	raw_response = response.read()
	API_CONNECTION.close()
	
	# parse results
	parsed_response = json.loads(raw_response)
	
	# return results
	if 'albums' in parsed_response:
		return parsed_response['albums']
	else:
		return None


# select mode
if len(sys.argv) > 1:
	if sys.argv[1] == 'interactive':
	
		print 'entering interactive mode'
		
		input_line = raw_input('> ')
		
		while input_line != 'exit':
			print 'you said: %s' % input_line
			
			quotations = extract_quotations(input_line)
			print 'quotations: %s' % quotations
			
			hashtags = extract_hashtags(input_line)
			print 'hastags: %s' % hashtags
			
			if quotations is not None and len(quotations) > 0:
				matching_albums = search_albums(quotations[0])
				print 'I found %d albums that match \"%s\", including \"%s\" - https://www.murfie.com/albums/%s' % (len(matching_albums), quotations[0], matching_albums[0]['album']['title'], matching_albums[0]['album']['slug'])
				
			if hashtags is not None:
				matching_albums = search_albums(hashtags[0][1:])
				if matching_albums is not None:
					message = 'I found %d albums that match %s, including \"%s\" - https://www.murfie.com/albums/%s' % (len(matching_albums), hashtags[0], matching_albums[0]['album']['title'], matching_albums[0]['album']['slug'])
					
					print message
					#post_response(message)
					
				else:
					print 'Sorry, I couldn\'t find any albums matching %s' % hashtags[0]
			
			input_line = raw_input('> ')
			
	else:
		print 'I don\'t understand that command, exiting'
else:
	print 'entering daemon mode'
	daemon_mode()
