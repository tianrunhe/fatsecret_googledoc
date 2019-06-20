import hashlib#for computing hash
from rauth.service import OAuth1Service #see https://github.com/litl/rauth for more info
import shelve #for persistent caching of tokens, hashes,etc.
import time
import datetime
from collections import defaultdict
#get your consumer key and secret after registering as a developer here: https://oauth.withings.com/en/partner/add

#FIXME add method to set default units and make it an optional argument to the constructor
class Fatsecret:
    KNOWN_USERS = { # (access_token, access_token_secret)
    }

    def __init__(self, consumer_key, consumer_secret):
        # Get a real consumer key & secret from https://dev.twitter.com/apps/new
        self.fatsecret = OAuth1Service(
            name='fatsecret',
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            request_token_url='http://www.fatsecret.com/oauth/request_token',
            access_token_url='http://www.fatsecret.com/oauth/access_token',
            authorize_url='http://www.fatsecret.com/oauth/authorize',
            base_url='http://platform.fatsecret.com/api/1.0/')

    def new_session(self):
        request_token, request_token_secret = self.fatsecret.get_request_token(params={'oauth_callback':'oob'})
        authorize_url = self.fatsecret.get_authorize_url(request_token)
        print 'Visit this URL in your browser: ' + authorize_url
        pin = raw_input('Enter PIN from browser: ')
        session = self.fatsecret.get_auth_session(request_token,
                                                request_token_secret,
                                                method='POST',
                                                data={'oauth_verifier': pin})
        print session.access_token, session.access_token_secret # Save this to database
        return session

    def reuse_session(self, user):
        access_token, access_token_secret = self.KNOWN_USERS[user]
        session = self.fatsecret.get_session((access_token, access_token_secret))
        return session

    def init_session(self, user):
        if user in self.KNOWN_USERS : session = self.reuse_session(user)
        else                        : session = self.new_session()
        return session


    def food_get(self,food_id):
        """Returns nutrition information and the corresponding fatsecret information URL for the specified food_id
        food_ids may be obtained by using foods_search()"""
        if food_id is None:
            return None
        params={'method': 'food.get','food_id':food_id,'format':'json'}
        response=self.oauth.get(
                'http://platform.fatsecret.com/rest/server.api',
                params=params,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
                header_auth=False)
        return response.content

    def foods_get_favorites(self):
        params={'method': 'foods.get_favorites','oauth_token': self.access_token,'format':'json'}

        response=self.oauth.get(
                'http://platform.fatsecret.com/rest/server.api',
                params=params,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
                header_auth=False)
        if response.content.get('foods'):
            return response.content['foods']['food']

    def foods_get_most_eaten(self,meal=None):
        params={'method': 'foods.get_most_eaten','oauth_token': self.access_token,'format':'json'}
        if meal in ['breakfast','lunch','dinner','other']:
            params['meal']=meal

        response=self.oauth.get(
                'http://platform.fatsecret.com/rest/server.api',
                params=params,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
                header_auth=False)
        if response.content.get('foods'):
            return response.content['foods']['food']

    def foods_get_recently_eaten(self,meal=None):
        params={'method': 'foods.get_recently_eaten','oauth_token': self.access_token,'format':'json'}
        if meal in ['breakfast','lunch','dinner','other']:
            params['meal']=meal

        response=self.oauth.get(
                'http://platform.fatsecret.com/rest/server.api',
                params=params,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
                header_auth=False)

        if response.content.get('foods'):
            return response.content['foods']['food']

    def foods_search(self,search_expression,page_number=None,max_results=None):
        params={'method': 'foods.search','oauth_token': self.access_token,'search_expression':search_expression,'format':'json'}
        if page_number!=None:
            params['page_number'] = page_number
        if max_results!=None:
            params['max_results'] = max_results

        response=self.oauth.get(
                'http://platform.fatsecret.com/rest/server.api',
                params=params,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
                header_auth=False)
        return response.content

    def food_entries_get(self,user,date=datetime.datetime.now()):
        params={'method': 'food_entries.get','format':'json'}
        session=self.init_session(user)
        response=session.get(
                'http://platform.fatsecret.com/rest/server.api',
                params=params)

        result = response.json()
        # if response.content['month'].get('day'):
        #     tmp=response.content['month']['day']
        # else:
        #     #months without data will still contain a 'month' key, but not a 'day' key
        #     tmp=None
        #result=[(i['carbohydrate'],i['fat'],i['protein'],i['calories'],i['date_int']) for i in tmp]
        food_entries = result['food_entries']['food_entry']
        meals = [(i['food_entry_name'],i['meal']) for i in food_entries]
        res = defaultdict(list)
        for v, k in meals: res[k].append(v)
        return res


    def saved_meals_get(self,user):
        """Returns a list where each item is formatted like
        {"saved_meal": {"meals": "Lunch,Other", "saved_meal_description": "A high impact energy meal - terrific for the great outdoors!", "saved_meal_id": "1111111", "saved_meal_name": "Power Snack" }"""
        params={'method': 'saved_meals.get','format':'json'}
        session = self.init_session(user)
        response=session.get(
                'http://platform.fatsecret.com/rest/server.api',
                params=params)
        if response.json().get('saved_meals'):
            tmp=response.json()['saved_meals']['saved_meal']
        else:
            tmp=None
        return tmp

    def weights_get_month(self,date=datetime.datetime.now()):
        """Return date_int and weight in kg for each day in requested month"""
        params={'method': 'weights.get_month','format':'json'}
        params['date']=int(round(time.mktime(date.timetuple())/60/60/24))
        response=self.oauth.get(
                'http://platform.fatsecret.com/rest/server.api',
                params=params,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
                header_auth=False)
        print response.content
        #note that every valid data point has weight_kg and date_int fields but
        #may also optionally have a weight_comment field
        #also note that you in response.content you also get from_date_int and to_date_int keys
        #that specify the range of dates included in the requested month
        if response.content['month'].get('day'):
            tmp=response.content['month']['day']
        else:
            tmp=None
        return tmp


    def exercise_entries_get_month(self,date=datetime.datetime.now()):
        """Return date_int and calories burned for each day in requested month"""
        params={'method': 'exercise_entries.get_month','format':'json'}
        params['date']=int(round(time.mktime(date.timetuple())/60/60/24))
        response=self.oauth.get(
                'http://platform.fatsecret.com/rest/server.api',
                params=params,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
                header_auth=False)
        print response.content
        #note that every valid data point has weight_kg and date_int fields but
        #may also optionally have a weight_comment field
        if response.content['month'].get('day'):
            tmp=response.content['month']['day']
        else:
            tmp=None
        return tmp
