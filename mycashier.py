#!/usr/bin/env python3
 
# Copyright (c) 2018 Amitabha Banerjee
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the file LICENSE.txt or at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import time

import anki_vector
from anki_vector.util import degrees
from anki_vector.events import Events
from anki_vector.screen import convert_pixels_to_screen_data

from anki_vector.objects import CustomObjectMarkers, CustomObjectTypes
from anki_vector.faces import Face
from coinbase.wallet.client import Client
import json
import functools
import os
import urllib

# Please enter the address of your bit coin account. As an example, you can get one at coinbase.com
_BTC_ADDRESS = 'Enter a valid bit coinaddress here'
# Please enter the API key and secret of a coinbase client here
_API_KEY = 'Enter the API key of a coinbase client here'
_API_SECRET = 'Enter the API secret here'

try:
    from PIL import Image
except ImportError:
    sys.exit("Cannot import from PIL: Do `pip3 install --user Pillow` to install")

#Defining a static mapping of all object types, corresponding text, and value
with open('pricing.json', 'r') as f:
   mapping = json.load(f)

scanAndPurchase = False

lookForFace = True

nextScan = True

bill = 5

_btcAddress = '<bit coin address>'

try:
    coinbaseClient = Client(_API_KEY, _API_SECRET)
except:
    print ("Error creating the coinbase client")

def handle_object_appeared(robot, event_type, event):
    """
        Handler for whenever an object appears
    """
    global bill
    global scanAndPurchase
    global nextScan
    # This will be called whenever an EvtObjectAppeared is dispatched -
    # whenever an Object comes into view.
    print("--------- Vector started seeing an object --------- \n{event.obj}")
    if scanAndPurchase and nextScan:
       nextScan = False
       if type(event.obj) is Face:
          print ("Face detected")
       else:
          print (event.obj)
          #object_type = "CustomType00"
          object_type = event.obj.archetype.custom_type
          print (object_type.name)
          robot.say_text(mapping[object_type.name]["description"])
          bill += mapping[object_type.name]["price"]
          print ("Current bill is %d" % bill)

def handle_object_disappeared(event_type, event):
    global nextScan
    # This will be called whenever an EvtObjectDisappeared is dispatched -
    # whenever an Object goes out of view.
    print("--------- Vector stopped seeing an object --------- \n{event.obj}")
    nextScan = True

def on_robot_observed_face(robot, event_type, event):
    global scanAndPurchase
    global lookForFace
    if lookForFace:
       print("--------- Vector sees a face --------- \n{event.obj}")
       robot.say_text("Welcome. I am your cashier. Please show me the items you\
       want to buy")
       lookForFace = False
       scanAndPurchase = True

def checkPayment(bitCoins):
    # Access Url and check for notification
    notifications = coinbaseClient.get_notifications()
    # Check if there exists a payment notification for the same amount
    if notifications.get("type") == "wallet:addresses:new-payment":
       #Process new payment
       additionalData = notification.get("additional_data")
       if additionalData:
          amount = additionalData.get("amount")
          if amount:
             bitCoinAmount = amount.get("amount")
             if bitCoinAmount == bitCoins:
                print("---Payment received and verified---")
                return True
    return False

def convertBillToBitcoin(bill):
   convertUrl = "https://blockchain.info/tobtc?currency=USD&value=%d" % bill
   res = urllib.request.urlopen(convertUrl).read()
   return res.decode("utf-8")

def downloadImage(imageId, bitcoinHash, amount):
   imageFName = 'BPay%d.png' % imageId
   bitcoinFloat = float(amount)
   bitcoinFloat = round(bitcoinFloat, 4)
   imageUrl =\
   'https://chart.googleapis.com/chart?chs=184x96&cht=qr&chl=bitcoin:%s&amount=%s'\
   % (bitcoinHash, bitcoinFloat)
   print (imageUrl)
   f = open(imageFName,'wb')
   f.write(urllib.request.urlopen(imageUrl).read())

def lightcube_tapped(robot, event_type, event):
    #Do all the post completion work here
    # Now generate a QR code image
    global scanAndPurchase
    global lookForFace
    global bill
    global _btcAddress
    robot.say_text("Ok, lets help you pay the bill")
    robot.say_text("Your bill is %d dollars" % bill)

    scanAndPurchase = False
    print("---------Lightcube tapped----------")
    robot.behavior.set_head_angle(degrees(45.0))
    current_directory = os.path.dirname(os.path.realpath(__file__))

    bitCoins = convertBillToBitcoin(bill)

    downloadImage(1, _btcAddress, bitCoins)
    image_path = os.path.join(current_directory, "BPay1.png")

    # Load an image
    image_file = Image.open(image_path)

    # Convert the image to the format used by the Screen
    print("Display image on Vector's face...")
    image_data = image_file.getdata()
    pixel_bytes = convert_pixels_to_screen_data(image_data, image_file.width, image_file.height)
    robot.screen.set_screen_to_color(anki_vector.color.Color(rgb=[255, 128, 0]), duration_sec=1.0)
    robot.screen.set_screen_with_image_data(pixel_bytes, 60, interrupt_running=True)
    result = checkPayment(bitCoins)
    if result:
        time.sleep(20)
        robot.say_text("Thank you. Your bill is now paid. Please enjoy your meal.")
        robot.anim.play_animation_trigger('GreetAfterLongTime')
        time.sleep(5)
        print("Thank you. Your bill is now paid. Please enjoy your meal.")
        time.sleep(5)
        lookForFace = True

def main():
    args = anki_vector.util.parse_command_args()
    with anki_vector.Robot(args.serial,
                           default_logging=False,
                           show_viewer=False,
                           show_3d_viewer=False,
                           enable_face_detection=True,
                           enable_camera_feed=False,
                           enable_custom_object_detection=True,
                           enable_nav_map_feed=True) as robot:
        # Add event handlers for whenever Vector sees a new object
        print ("Disconnecting from any connected cube...")
        robot.world.disconnect_cube()
        print("Going to wait for 3 seconds to shut off all connections")
        time.sleep(5)
        print("Woken up")

        connectionResult = robot.world.connect_cube()
        print (connectionResult)

        connected_cube = robot.world.connected_light_cube
        print (connected_cube)
        if connected_cube:
           print("Connected to cube {0}".format(connected_cube.factory_id))
           robot.world.flash_cube_lights()
        robot.behavior.set_head_angle(degrees(35.0))
        robot.behavior.set_lift_height(0.0)
        on_object_appeared = functools.partial(handle_object_appeared, robot)
        robot.events.subscribe(on_object_appeared, anki_vector.events.Events.object_appeared)
        robot.events.subscribe(handle_object_disappeared, anki_vector.events.Events.object_disappeared)
        on_lightcube_tapped = functools.partial(lightcube_tapped, robot)
        robot.events.subscribe(on_lightcube_tapped, Events.object_tapped)

        if_robot_observed_face = functools.partial(on_robot_observed_face, robot)
        robot.events.subscribe(if_robot_observed_face, Events.robot_observed_face)

        # define a unique cube (44mm x 44mm x 44mm) (approximately the same size as Vector's light cube)
        # with a 50mm x 50mm Circles2 image on every face. Note that marker_width_mm and marker_height_mm
        # parameter values must match the dimensions of the printed marker.
        cube_obj = robot.world.define_custom_cube(custom_object_type=CustomObjectTypes.CustomType00,
                                                  marker=CustomObjectMarkers.Circles2,
                                                  size_mm=44.0,
                                                  marker_width_mm=50.0,
                                                  marker_height_mm=50.0,
                                                  is_unique=True)

        # define a unique cube (88mm x 88mm x 88mm) (approximately 2x the size of Vector's light cube)
        # with a 50mm x 50mm Circles3 image on every face.
        big_cube_obj = robot.world.define_custom_cube(custom_object_type=CustomObjectTypes.CustomType01,
                                                      marker=CustomObjectMarkers.Circles3,
                                                      size_mm=44.0,
                                                      marker_width_mm=50.0,
                                                      marker_height_mm=50.0,
                                                      is_unique=True)

        if ((cube_obj is not None) and (big_cube_obj is not None)):
            print("All objects defined successfully!")
        else:
            print("One or more object definitions failed!")
            return

        try:
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
