#!/usr/bin/env python
# encoding: utf-8
"""
V for Vector main.py

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

import sys
import time
import getopt
import threading
import datetime
import inflect
import random
import traceback

from datetime import datetime

import anki_vector
from anki_vector.events import Events
from anki_vector.util import degrees
from anki_vector.faces import Expression
from anki_vector.connection import ControlPriorityLevel
from anki_vector.util import distance_mm, speed_mmps
from anki_vector.util import degrees
from anki_vector.behavior import MIN_HEAD_ANGLE, MAX_HEAD_ANGLE

from jira import JiraChecker

class V4Vector(object):

  RANDOM_CITIZEN = 'Random citizen'
  RANDOM_CITIZEN_SET = set({RANDOM_CITIZEN})

  ANYONE_HERE = set({
    'Is there anyone here?',
    'Hello?',
    "I'm lonely ...",
    'Where is everyone?'
  })
    
  def __init__(self, vector=None):
    '''
    Initializing main class
    '''
    self.vector = vector
    self.jira = JiraChecker()
    self.inflect_engine = inflect.engine()
    self.robot = None
    self.rotation = 0
    self.last_seen_human_rotation = dict()
    self.last_seen_human = dict()
    self.can_rotate = True

    print("Initialized")


  def __find_faces(self):
    '''
    Extended version of the find faces algoritm
    '''
    timeout = 10
    if self.can_rotate:
      if len(self.detected_faces) is 0:
        self.robot.behavior.say_text(random.choice(list(V4Vector.ANYONE_HERE)), duration_scalar=1.5)

      self.__clean_up_detected_faces()
      self.robot.behavior.drive_off_charger()

      head_angle = random.randint(35, 45)
      rotate_angle = random.randint(30, 90)

      self.rotation += rotate_angle
      self.rotation %= 360

      print(f"------ Vector will look for humans (rotation: {self.rotation}, rotate: {rotate_angle}, head: {head_angle}, timeout: {timeout})! ------")

      self.robot.behavior.set_head_angle(degrees(head_angle))
      self.robot.behavior.turn_in_place(degrees(rotate_angle), angle_tolerance=degrees(0))
      # self.robot.behavior.drive_straight(distance_mm(random.randint(-10, 10)), speed_mmps(100))

    threading.Timer(timeout, self.__find_faces).start()


  def __clean_up_detected_faces(self):
    '''
    Call to ensure that we can talk to the human again
    '''
    now = datetime.now()

    self.detected_faces = set([
      user_name 
      for user_name in self.detected_faces
      if (now - self.last_seen_human.get(user_name, now)).seconds < 60
    ])


  def __find_jira_tickets(self):
    '''
    Will periodically check for new jira tickets
    '''
    new_jira_tickets = self.jira.check_for_new_jira_tickets(self.last_seen_human)

    if new_jira_tickets['total'] > 0:
      users_with_tickets = set([
        self.jira.get_user_name(issue['assignee'])
        for issue in new_jira_tickets['issues']
      ])

      print(f"found users with tickets {users_with_tickets}")

      for user in users_with_tickets:
        self.last_seen_human[user] = datetime.now()

        rotations = self.last_seen_human_rotation.get(user, [])
        if rotations:
          rotate_angle = rotations[0] - self.rotation

          print(f'Rotations: {rotate_angle}, {self.rotation}, {rotations}')

          tickets_for_user = [
            issue['summary'] 
            for issue
            in new_jira_tickets['issues']
            if self.jira.get_user_name(issue['assignee']) is user
          ]

          tickets_count = len(tickets_for_user)

          self.robot.behavior.say_text(f'I\'m looking for {user}, you have {tickets_count} new jira { self.inflect_engine.plural("ticket", tickets_count) }')

          self.rotation = rotations[0]
          self.robot.behavior.turn_in_place(degrees(rotate_angle), angle_tolerance=degrees(0))

          for idx, ticket in enumerate(tickets_for_user):
            self.robot.behavior.say_text(f"Issue number {idx+1}: {ticket}", duration_scalar=0.9, use_vector_voice=False)

    threading.Timer(60, self.__find_jira_tickets).start()



  def __get_emotions(self, face):
    '''
    Parses face emotions into (emotion, positive) tuple
    '''
    if face.expression is Expression.HAPPINESS.value:
      emotion = 'happy'
      positive_emotion = True
    elif face.expression is Expression.SURPRISE.value:
      emotion = 'surprised'  
      positive_emotion = True
    elif face.expression is Expression.ANGER.value:
      emotion = 'angry'
      positive_emotion = False
    elif face.expression is Expression.SADNESS.value:
      emotion = 'sad'
      positive_emotion = False
    else:
      emotion = ''
      positive_emotion = None

    return emotion, positive_emotion


  def __get_text_to_say(self, face, face_name, jira_tickets):
    '''
    Generates text to be said
    '''
    emotion, positive_emotion = self.__get_emotions(face)

    if face.name is not '':

      jira_tickets_total = jira_tickets['total']

      if jira_tickets_total < 1:
        if positive_emotion is True:
          joiner = f', is that why you are {emotion}?'
        elif positive_emotion is False:
          joiner = f', so why are you {emotion}?'
        else:
          joiner = '!'
        say_text = f"{face_name}, you have no new jira tickets{joiner}"

      else:
        if positive_emotion is False:
          joiner = f', is that why you are {emotion}?'
        elif positive_emotion is True:
          joiner = f', so why are you {emotion}?'
        else:
          joiner = '!'

        say_text = f"{face_name}, you have {jira_tickets_total} jira { self.inflect_engine.plural('ticket', jira_tickets_total) }{joiner}"

    else:
      say_text = f"I see you {emotion}, {face_name}!"

    return say_text


  def _on_robot_observed_face(self, robot, event_type, event, evt):
    '''
    Event handler for when Vector sees face
    '''
    self.can_rotate = False

    faces = [ face for face in robot.world.visible_faces ]
    print(f"Vector sees faces: {faces}, {datetime.now()} {event_type}")

    for face in faces:
      face_name = face.name if face.name is not '' else V4Vector.RANDOM_CITIZEN

      if face_name not in self.detected_faces:
        try:
          self.detected_faces.add(face_name)
          self.last_seen_human_rotation[face_name] = self.last_seen_human_rotation.get(face_name, []) + [self.rotation]
          self.last_seen_human[face_name] = datetime.now()
          jira_tickets = self.jira.check_tickets_for_user(face.name, face.time_since_last_seen) 
          say_text = self.__get_text_to_say(face, face_name, jira_tickets)
          robot.behavior.say_text(say_text, use_vector_voice=False)

          for idx, ticket in enumerate(jira_tickets['issues']):
            robot.behavior.say_text(f"Issue number {idx+1}: {ticket['summary']}", duration_scalar=0.9, use_vector_voice=False)

        except:
          print(sys.exc_info()[0])
          print(traceback.format_exc())
      else:
        print(face_name)

    self.can_rotate = True


  def run(self):
      self.detected_faces = set()

      with anki_vector.Robot(enable_face_detection=True) as robot:
        self.robot = robot
        robot.vision.enable_face_detection(estimate_expression=True)
        robot.vision.enable_display_camera_feed_on_face()
        robot.behavior.set_head_angle(degrees(45.0))
        robot.behavior.set_lift_height(0.0)

        evt = threading.Event()
        robot.events.subscribe(self._on_robot_observed_face, Events.robot_observed_face, evt)
        threading.Timer(10, self.__find_faces).start()
        threading.Timer(60, self.__find_jira_tickets).start()

        print("------ waiting for face events, press ctrl+c to exit early ------")

        try:
          if not evt.wait(timeout=12000):
            print("----- that's all folks ------")
        except KeyboardInterrupt:
          pass

        robot.events.unsubscribe(self._on_robot_observed_face, Events.robot_observed_face)



# ====================================

help_message = '''
TODO: This will tell how to call this V for Vector script.

--vector  Vector name
'''

class Usage(Exception):
  def __init__(self, msg):
    self.msg = msg


def main(argv=None):
  if argv is None:
    argv = sys.argv
  try:
    vector = None
    
    try:
      opts, args = getopt.getopt(argv[1:], "hv:", ["help", "vector="])
    except getopt.error as msg:
      raise Usage(msg)

    # option processing
    for option, value in opts:
      if option in ("-h", "--help"):
        raise Usage(help_message)
      if option in ("-v", "--vector"):
        vector = value

    v = V4Vector(vector)
    v.run()
    
  
  except Usage as err:
    print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
    print >> sys.stderr, "\t for help use -h or --help "
    return 2

if __name__ == "__main__":
  main()
