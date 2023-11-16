# Project: Count GPT - test GPT's ability to count LEDs
# Author - Stephen Witty switty@level500.com
# Started 11-15-23
# Description - turn on random LEDs via Pi GPIO pins, take picture via Pi camera, send to GPT and ask to count lights, keep stats
# The GPT prompt is looking for red LEDs
# Example  used  from openai for vision gpt
# To run:
#     install python lib: adafruit-blinka (for GPIO)
#     install  banner command: sudo apt-get install sysvbanner
#     System uses Raspberry Pi GPIO outputs 1 through 5 to turn on LEDs
#     System uses standard Raspberry Pi camera for taking pictures with lib-camera-jpeg
#
# V1 11-15-23   Initial development

import busio
import RPi.GPIO as GPIO
import random
import time
import os
import base64
import requests

# OpenAI API Key
api_key = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

##################### Constants #######################################################
NUM_LEDS = 5                                  # Number of LEDs enabled, start at GPIO1
RANDOM_WEIGHT = 1                             # Higher number = less leds turned on
COUNT = 10                                    # Number of times to run the test
PIC_NAME = "/home/pi/dev/openai/image.jpg"    # Image name and location fully pathed
#######################################################################################

# Function to encode the image
def encode_image(image_path):
   with open(image_path, "rb") as image_file:
      return base64.b64encode(image_file.read()).decode('utf-8')

# Setup GPIO leds - using pins 1 through NUM_LEDs (not pin zero)
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
for i in range(1,NUM_LEDS + 1):
   GPIO.setup(i,GPIO.OUT)
   GPIO.output(i,1)

###################### Main loop ############################
total = 0
web_api_error = 0
no_answer = 0
wrong_answer = 0
right_answer = 0

while (total < COUNT):
   if (total !=0):
      time.sleep(3)
   lit = 0
   while(lit == 0): # Make sure that at least one led is lit
      for i in range(1,NUM_LEDS + 1):
         if (random.randint(0,RANDOM_WEIGHT) == 0):
            GPIO.output(i,1)
            lit = lit + 1
         else:
            GPIO.output(i,0)

   os.system("rm -f " + PIC_NAME)
   os.system("libcamera-jpeg -o " + PIC_NAME + " 1>/dev/null 2>/dev/null")

   total = total + 1

   # Path to your image
   image_path = PIC_NAME

   # Getting the base64 string
   base64_image = encode_image(image_path)

   headers = {
      "Content-Type": "application/json",
      "Authorization": f"Bearer {api_key}"
   }

   payload = {
      "model": "gpt-4-vision-preview",
      "messages": [
         {
            "role": "user",
            "content": [
               {
                  "type": "text",
                  "text": "How many red LED lights are lit in the image?  Provide back the answer as a number between {}.  For example if the answer is 2 then reply back with {2}.  Provide no other description or details."
               },
               {
                  "type": "image_url",
                  "image_url": {
                     "url": f"data:image/jpeg;base64,{base64_image}"
               }
            }
         ]
      }
   ],
    "max_tokens": 300
   }

   output = {}
   try:
      response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=90)
      output = response.json()
   except Exception as e:
      print("ERROR - Exception on openai web call.")
      print(e)
      web_api_error = web_api_error + 1
      continue

   if (response.status_code != 200  or "error" in output):
      print("ERROR - Received return error from openai web api.  Status code = " + str(response.status_code))
      web_api_error = web_api_error + 1
      if ("error" in output):
         print(output["error"]["message"])
      continue

   if ("choices" not in output):
      print("ERROR - Choices is not in output from GPT")
      web_api_error = web_api_error + 1
      continue

   message = output["choices"][0]["message"]["content"]
#   message = "This is a test {}"
   print("\n" + message + "\n")

################### Extract GPT answer from {} #######################
   cnt = 0
   cnt2 = 0
   pos = 0
   for char in message:
      if (char == "{"):
         cnt = cnt + 1
         start = pos
      if (char == "}"):
         cnt2 = cnt2 + 1
         end = pos
      pos = pos + 1

   if (cnt == 0 or cnt2 == 0):
      print("ERROR:  No brackets or incomplete")
      no_answer = no_answer + 1
      continue

   if (cnt > 1 or cnt2 > 1):
      print("ERROR:  Too many brackets in output from GPT")
      no_answer = no_answer + 1
      continue

   if (end < start):
      print("ERROR: Brackets are reversed in output from GPT")
      no_answer = no_answer + 1
      continue

   if ( (end - start) != 2 and (end - start) != 3):
      print("ERROR: No single or double digit number in between brackets")
      no_answer = no_answer + 1
      continue

   move_char = message[start + 1]
   if not (move_char.isdigit()):
      print("ERROR: First character is not a digit")
      no_answer = no_answer + 1
      continue

   move_char2 = ""
   if ((end - start) == 3):
      move_char2 = message[start + 2]
      if not (move_char2.isdigit()):
         print("ERROR: Second character is not a digit")
         no_answer = no_answer + 1
         continue 

   answer = int(move_char + move_char2)
   if (answer < 0 or answer > 99):
      print("ERROR:  Answer is out of range")
      no_answer = no_answer + 1
      continue
################ End Extract GPT answer #######

   os.system("banner " + "\"LEDs  " + str(lit) + "\"")
   os.system("banner " + "\"Gpt   " + str(answer) + "\"")

   # Keep track of the number of right and wrong answers 
   if (lit == answer):
      right_answer = right_answer + 1
   else:
      wrong_answer = wrong_answer + 1

print("**************** End Report ********************")
print("Web API errors: " + str(web_api_error))
print("Bad answer format: " +  str(no_answer))
print("Right answers: " + str(right_answer))
print("Wrong answers: " + str(wrong_answer))
print("************************************************")
