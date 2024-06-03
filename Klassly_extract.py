import requests
import json
import time
from datetime import datetime
import os.path
import os
import hashlib

# Load configuration file
with open("config.json", "r") as f:
    config = json.load(f)
    
# Start requests module
session = requests.Session()
session.headers = {'User-Agent': config['headers']}

# Retrieve
response = session.get(config['KLASSLY']['URL_START'])
if response.status_code != 200 :
    exit(config['KLASSLY']['URL_START'] + " : we don't retrieve the startpage.")

POST_data = {'phone' : config['phone'],
             'password' : config['password'],
             'auth_token' : 'null',
             'device' : session.cookies.get_dict()['klassroom_device'],
             'app-id' : config['KLASSLY']['app-id'],
             'version' : config['KLASSLY']['version'],
             'culture' : config['KLASSLY']['culture'],
             'apptype' : config['KLASSLY']['apptype'],
             'gmt_offset' : config['KLASSLY']['gmt_offset'],
             'tz' : config['KLASSLY']['tz'],
             'dst' : config['KLASSLY']['dst'],
             }

# Log-in
response = session.post(config['KLASSLY']['URL_LOGIN'], data=POST_data)
data = response.json()
POST_data['auth_token'] = data['auth_token']
POST_data['klassroom_token'] = data['auth_token']

# Find all klasses
response = session.post(config['KLASSLY']['URL_CONNECT'], data=POST_data)

data = response.json()

# How do we retrieve the klassroomauth in case of multiple klasses ?
# I don't know. Surprise ! Surprise !
cookies = {
    'klassroomauth' : data['pixel'],
    }

i=0
attempt_datetime=0
max_datetime = 0

for klassroom in data['klasses']:
    
    POST_data['from'] = datetime.timestamp(datetime.now())*1000
    POST_data['type'] = config['KLASSLY']['type']
    POST_data['filter'] = config['KLASSLY']['filter']
    POST_data['id'] = klassroom

    while True :
        response = session.post(config['KLASSLY']['URL_HISTORY'], data=POST_data)
        data = response.json()

        # For each post, turn in all attachment to retrieve photos.
        for post_key, post_values in data['posts'].items():
            max_datetime = max(max_datetime,config['last_timestamp'],post_values['date'])
            for photo in post_values['attachments'].values():
               
                if int(post_values['date']) > config['last_timestamp'] :
#                     print('date_time  : {} - last_timestamp {}'.format(post_values['date'], config['last_timestamp']))
                    # Prepare date_time and photo variable
                    date_time = datetime.fromtimestamp(post_values['date']/1000)
                    photo_name = date_time.strftime("%Y-%m-%d") + " - "+ photo['name'].split(".")[0]
                    photo_copy = ""
                    photo_extension = "."+photo['name'].split(".")[1]
                    photo_url = photo['url'].split("/")[-1]
                    
                    if config['DEBUG']['DEBUG_RETRIEVE']:
                        # Retrieve photo and save it. If needed, attempt 3 times
                        for attempt_photo in range(config['TRIES_PHOTOS']):
                            try:
                                response = session.get(config['KLASSLY']['URL_IMG']  +photo_url, cookies=cookies)
                                
                                if (response.status_code == 200 and config['DEBUG']['DEBUG_SAVE']):
                                    while(os.path.exists(config['FOLDER_SAVE']+photo_name+photo_copy+photo_extension)):
                                        if photo_copy == "":
                                            i=1
                                            photo_copy = "("+str(i)+")"
                                        else:
                                            i=i+1
                                            photo_copy = "("+str(i)+")"
                                    with open(config['FOLDER_SAVE']+photo_name+photo_copy+photo_extension, mode="wb") as file:
                                        file.write(response.content)
                                    print(photo_name+photo_copy+photo_extension + " : OK")
                                        
                                else:
                                    print(config['KLASSLY']['URL_IMG'] + photo_url + " : it looks like we have a problem, sir ! ("+response.status_code+")")
                            except requests.exceptions.ConnectionError:
                                time.sleep(config['TIME_BETWEEN_TWO_ATTEMPTS'])
                            else:
                                break
                        else:
                            print(str(i) + " - " + photo_name)
                        time.sleep(config['TIME_BETWEEN_TWO_PHOTOS'])
        if post_values['date'] < POST_data['from']:
            POST_data['from'] = post_values['date']
        elif attempt_datetime == config['TRIES_DATETIME']:
            break
        else:
            attempt_datetime = attempt_datetime + 1
        

# check for duplicated files based on the date and the md5 check
# If duplicated, remove the last one
md5_list = []

for file_name in os.listdir(config['FOLDER_SAVE']):
    date = file_name[0:10]
    with open(config['FOLDER_SAVE'] + "/"+ file_name, 'rb') as file_to_check:
        data = file_to_check.read()
        md5_returned = hashlib.md5(data).hexdigest()
        if date+md5_returned in md5_list:
            os.remove(config['FOLDER_SAVE']+"/"+file_name)
        else:
            md5_list.append(date+md5_returned)

# Check if a unnumbered file name exists 
# If not, rename the file witouth them
# Else try a number in the file name
for try_rename in range(config['TRIES_RENAME']):
    for file_name in os.listdir(config['FOLDER_SAVE']):
        if "(" in file_name:
            file_name_begin = file_name.split("(")[0]
            extension = file_name.split(")")[-1]
            number = ""
            while (os.path.exists(config['FOLDER_SAVE']+file_name_begin+number+extension)):
                if number == "":
                    i=1
                    number = "("+str(i)+")"
                else:
                    i=i+1
                    number = "("+str(i)+")"
            os.rename(config['FOLDER_SAVE']+file_name,config['FOLDER_SAVE']+file_name_begin+number+extension)



config['last_timestamp'] = max_datetime
#write it back to the file
with open('config.json', 'w') as f:
    json.dump(config, f, indent=4)