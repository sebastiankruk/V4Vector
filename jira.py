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
    with open('jira-connection.json') as jira_connection_file:
      self.connection = json.load(jira_connection_file)

    self.jira_url = f"{self.connection['url']}/rest/api/2/search"
    self.jira_query_template = {
        "startAt": 0,
        "maxResults": 100,
        "fields": [
          "key",
          "summary",
          "created"
        ]
    }
    self.jira_query_jql_template = '''issuetype in (Bug) AND assignee = "%s" AND status in (New)'''
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


  def __cleanup_summary(self, summary):
    '''
    '''
    return re.sub(r'[.,/;:]', ' ', summary)

  def __prepare_jira_response(self, response, new_since):
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
          'created': datetime.strptime(issue['fields']['created'], "%Y-%m-%dT%H:%M:%S.%f%z")
        }
        for issue in response_json['issues']
      ] 
    }
    return results


  def check_tickets_for_user(self, name, new_since=None):
    '''
    Will call Jira and check whether there are any tickets currently assigned to the user
    '''
    email = self.__get_user_email(name)

    if email is not None:
      jira_query = dict(self.jira_query_template)
      jira_query['jql'] = self.jira_query_jql_template % email

      response = requests.post(self.jira_url, json.dumps(jira_query), headers=self.jira_headers)

      if response.status_code is 200:
        return self.__prepare_jira_response(response, new_since)

    else:
      print(f"Could not match user {name}")

    return {
      'total': 0,
      'issues':[]
    }
  
