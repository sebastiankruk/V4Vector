#!/usr/bin/env python
# encoding: utf-8
"""
V for Vector jira.py

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Created by Sebastian Kruk and Michał Szopiński
"""

import re
import json
from  datetime import datetime
import requests

class JiraChecker:
  '''
  Class responsible for managing whole communication with Jira
  '''

  def __init__(self, *args, **kwargs):
    '''
    Initializes JiraChecker by loading configuration files: jira-users.json and jira-connection.json
    '''
    with open('jira-users.json') as jira_users_file:
      self.users = json.load(jira_users_file)

    self.emails = {
      value['email']: key
      for key, value
      in self.users.items()
    }

    with open('jira-connection.json') as jira_connection_file:
      self.connection = json.load(jira_connection_file)

    self.jira_url = f"{self.connection['url']}/rest/api/2/search"
    self.jira_query_template = {
        "startAt": 0,
        "maxResults": 100,
        "fields": [
          "key",
          "summary",
          "created",
          "assignee"
        ]
    }
    self.jira_query_jql_template = '''issuetype in (Bug) AND assignee = "%s" AND status in (New)'''
    self.jira_update_query_jql_template = '''issuetype in (Bug) AND status in (New) AND (%s) ORDER BY created ASC'''
    self.jira_user_date_template = '''(assignee = "%s" AND updatedDate > "%s")'''

    self.jira_headers = {
      'Authorization': f'''Basic {self.connection['auth']}''',
      'Content-Type': 'application/json'
    }


  def __get_user_email(self, name):
    '''
    Finds user email based on the given name
    '''
    user = self.users.get(name, {'email': None})
    return user['email']

  def get_user_name(self, email):
    '''
    Finds user name based on the given email
    '''
    return self.emails.get(email, None)

  def __cleanup_summary(self, summary):
    '''
    '''
    return re.sub(r'[.,/;:]', ' ', summary)

  def __prepare_jira_response(self, response):
    '''
    Repackages response from jira
    '''
    response_json = response.json()
    results = {
      'total': response_json['total'],
      'total_since_last_seen': 0,
      'issues': [
        {
          'summary': self.__cleanup_summary(issue['fields']['summary']),
          'created': datetime.strptime(issue['fields']['created'], "%Y-%m-%dT%H:%M:%S.%f%z"),
          'assignee': issue['fields']['assignee']['name']
        }
        for issue in response_json['issues']
      ] 
    }
    return results

  def _call_jira(self, jql=None):
    '''
    Helper method to call jira
    '''
    if jql:
      jira_query = dict(self.jira_query_template)
      jira_query['jql'] = jql
      
      s_jira_query = json.dumps(jira_query)

      print(s_jira_query)
      response = requests.post(self.jira_url, s_jira_query, headers=self.jira_headers)

      if response.status_code is 200:
        return self.__prepare_jira_response(response)

    return {
      'total': 0,
      'issues':[]
    }



  def check_tickets_for_user(self, name, new_since=None):
    '''
    Will call Jira and check whether there are any tickets currently assigned to the user
    '''
    email = self.__get_user_email(name)

    if email is not None:
      return self._call_jira(jql=self.jira_query_jql_template % email)
    else:
      print(f"Could not match user {name}")

    return self._call_jira()


  
  def check_for_new_jira_tickets(self, last_seen_users):
    '''
    Will do a special call to Jira to get the list of user
    '''
    if last_seen_users:
      jira_query_users = ' OR '.join([
        self.jira_user_date_template % ( self.__get_user_email(user_name), last_seen.strftime('%Y-%m-%d %H:%M') )
        for (user_name, last_seen) 
        in last_seen_users.items()
      ])
      
      return self._call_jira(jql=self.jira_update_query_jql_template % jira_query_users)

    return self._call_jira()
