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
import getopt
import threading
import datetime
import inflect
import random

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
    
  def __init__(self, vector=None):
    '''
    Initializing main class
    '''
    self.vector = vector
    self.jira = JiraChecker()
    self.inflect_engine = inflect.engine()

    print("Initialized")


  def __find_faces(self, robot):
    '''
    Extended version of the find faces algoritm
    '''
    actions = random.choices(('drive', 'head', 'turn'), k=random.randint(1,3))

    print(f"------ Vector will look for faces {actions}! ------")

    if 'head' in actions:
      robot.behavior.set_head_angle(degrees(random.randint(0, 45)))
    if 'drive' in actions:
      robot.behavior.drive_straight(distance_mm(random.randint(50, 100)), speed_mmps(100))
    if 'turn' in actions:
      robot.behavior.drive_off_charger()
      robot.behavior.turn_in_place(degrees(random.randint(-90, 90)))
    #find_faces
    #look_around_in_place
    

  def run(self):
      self.said_text = False
      self.detected_faces = set()

      def on_robot_observed_face(robot, event_type, event, evt):
        self.said_text
        if not self.said_text:

          # print(f"Vector sees a face {datetime.datetime.now()}")

          faces = list()
          for face in robot.world.visible_faces:
            faces.append(face)

          for face in faces:

            if not face.name in self.detected_faces:
              print("Face!")

              try:
                if face.expression is Expression.HAPPINESS.value:
                  emotion = 'are happy'
                elif face.expression is Expression.ANGER.value:
                  emotion = 'are angry'
                elif face.expression is Expression.SADNESS.value:
                  emotion = 'are sad'
                elif face.expression is Expression.SURPRISE.value:
                  emotion = 'are surprised'  
                else:
                  emotion = ''

                face_name = face.name if face.name is not '' else 'Random citizen'

                robot.behavior.say_text(f"I see you {emotion}, {face_name}!")
                self.detected_faces.add(face_name)

                if face.name is not '':
                  jira_tickets = self.jira.check_tickets_for_user(face.name, face.time_since_last_seen)
                  jira_tickets_total = jira_tickets['total']
                  if jira_tickets_total < 1:
                    robot.behavior.say_text(f"You have no new jira tickets")
                  else:
                    robot.behavior.say_text(f"You have {jira_tickets_total} jira { self.inflect_engine.plural('ticket', jira_tickets_total) }")

                  for ticket in jira_tickets['issues']:
                    robot.behavior.say_text(f"{ticket['summary']}")

                # self.said_text = True
                # print(f"Face: {face.name}, {face.expression}")
              except Exception as e:
                print(e)

          # evt.set()

      with anki_vector.Robot(enable_face_detection=True, behavior_control_level=ControlPriorityLevel.OVERRIDE_BEHAVIORS_PRIORITY) as robot:
        robot.vision.enable_face_detection(estimate_expression=True)
        robot.vision.enable_display_camera_feed_on_face()

        # If necessary, move Vector's Head and Lift to make it easy to see his face
        robot.behavior.set_head_angle(degrees(45.0))
        robot.behavior.set_lift_height(0.0)


        evt = threading.Event()
        # robot.events.subscribe(on_robot_observed_face, Events.robot_changed_observed_face_id, evt)
        robot.events.subscribe(on_robot_observed_face, Events.robot_observed_face, evt)

        print("------ waiting for face events, press ctrl+c to exit early ------")

        try:
          while True:
            if not evt.wait(timeout=15):
              # robot.behavior.find_faces()
              self.__find_faces(robot)
              self.detected_faces.clear()
        except KeyboardInterrupt:
          pass

      robot.events.unsubscribe(on_robot_observed_face, Events.robot_observed_face)



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
