import os
import json
from os.path import exists
import datetime
from configparser import ConfigParser
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.authorization import AuthorizeResult
from slack_sdk.oauth.installation_store import FileInstallationStore, Installation
from slack_sdk.oauth.state_store import FileOAuthStateStore
from slack_bolt.oauth.oauth_settings import OAuthSettings

configur = ConfigParser()
configur.read('config.ini')

oauth_settings = OAuthSettings(
    client_id=configur.get("config2","SLACK_CLIENT_ID"),
    client_secret=configur.get("config2","SLACK_CLIENT_SECRET"),
    scopes=["chat:write.customize", "chat:write"],
    user_scopes=["im:history", "im:read", "users:read", "users:write","chat:write"],
    installation_store=FileInstallationStore(base_dir="./data/installations"),
    state_store=FileOAuthStateStore(expiration_seconds=600, base_dir="./data/states")
)

# Initializes your app with your bot token and socket mode handler
app = App(
    signing_secret=configur.get("config2","SLACK_SIGNING_SECRET"),
    oauth_settings=oauth_settings
)


# this variable (user_id) is used to store the userId of the current user
user_id = ""


# this variable (rec) is used to store the ID of reciever
# this will be used in the following methods - respond(event, say, context, client, body )
rec =""

# message is an event handler refer: https://api.slack.com/events ; 
@app.event("message") 
def respond(event, say, context, client, body ):
    
    USER_TOKEN = context.user_token #sender
    sender = event["user"]
    receiver = body["authorizations"][0]["user_id"]
    print(body)
    
    # this variable (rec) is used to store the ID of reciever
    # this will be used in the following methods - respond(event, say, context, client, body )
    global rec 

    rec = receiver # storing the reciver id in rec

    # for info on methods: https://api.slack.com/methods
    user_presence = app.client.users_getPresence(
        user = receiver, 
        token = USER_TOKEN
    )["presence"]
    user_info = app.client.users_info(
        user = receiver,
        token = USER_TOKEN
    )["user"]
    
    print('sender: '+sender)
    print('reciver: '+receiver)
    if (user_presence == "away") and (user_info["profile"]["status_text"]== "Out of Office") and (not sender == receiver):
        try:
            installation_store = FileInstallationStore(base_dir="./data/installations")
            x = installation_store.find_installation(
                enterprise_id = user_info.get("enterprise_id",None),
                team_id = user_info["team_id"],
                user_id = user_info["id"],
                is_enterprise_install = user_info.get("is_enterprise_install",False),
            )
            RECEIVER_TOKEN = x.user_token
        except:
            print('failed to fetch receiver user token')
        else:
            # message last read by receiver
            try:
                last_read = app.client.conversations_info(
                    token = RECEIVER_TOKEN, 
                    channel = event["channel"]
                )["channel"]["last_read"]
                
                # check whether we have already replied in the current date. skip if yes
                # after 10 texts reply again to remind we are out of office

                message_list = app.client.conversations_history(
                    token = RECEIVER_TOKEN, 
                    channel = event["channel"], 
                    oldest = last_read, 
                )["messages"]

                replied = False
                for idx, message in enumerate(message_list):
                    # reply for every 10 Unresponded texts
                    if idx == 9:
                        break
                    if "Out of Office" in message["text"]:
                        replied = True
                        break

                if not replied:
                    expiration = user_info["profile"]["status_expiration"]
                    if not expiration == 0:
                        dt = datetime.datetime.fromtimestamp(expiration)
                        if exists('default_text.txt'):
                            with open('default_text.txt', 'r') as fp:
                                l = fp.read()
                                dic = {}
                                dic = json.loads(l)
                                
                                # rec is used to store the ID of reciever
                                # this will be used in the following methods - respond(event, say, context, client, body )

                                if rec in dic:
                                    text = f"Hi, <@{ sender }>!!! "+dic[rec]+f' and will be back on {dt}'
                                else:
                                    print("reached_else")
                                    text = f"Hi, <@{ sender }>!!!\nI am Out of Office and will be back on {dt}"            
                        else:        
                            text = f"Hi, <@{ sender }>!!!\nI am Out of Office and will be back on {dt}"
                    else:
                        # add career manager instead of U032ATMNLVC or any other profile field that may exist.
                        if exists('default_text.txt'):
                            with open('default_text.txt', 'r') as fp:
                                l = fp.read()
                                dic = {}
                                dic = json.loads(l)

                                # rec is used to store the ID of reciever
                                # this will be used in the following methods - respond(event, say, context, client, body )
                                if rec in dic:
                                    text = f"Hi, <@{ sender }>!!! "+dic[rec]
                                else:
                                    text = f"Hi, <@{ sender }>!!!\nI'll be Out of Office for a while.\nIn case of emergency please reach out to <@U032ATMNLVC>.\nThanks"            
                        else:
                            text = f"Hi, <@{ sender }>!!!\nI'll be Out of Office for a while.\nIn case of emergency please reach out to <@U032ATMNLVC>.\nThanks"
                    app.client.chat_postMessage(
                        # respond as Bot with Reciever Details
                        # token = RECEIVER_TOKEN, 
                        # username = user_info["name"],
                        # icon_url = user_info["profile"]["image_24"],
                        token = RECEIVER_TOKEN,
                        channel = sender,
                        text = text,
                    )
                else:
                    print("Already Replied")
                    pass
            except Exception as err:
                print(err)

def create_field(text, value):
    '''
    Creates the options in the required format
    '''
    data = {
        "text": {
            "type": "plain_text",
            "text": text,
        },
        "value": value
    }
    return data


def create_initial_options(body,block_name,block_action):
    return create_field(
        body['view']['state']['values'][block_name][block_action]['selected_option']['text']['text'],
        body['view']['state']['values'][block_name][block_action]['selected_option']['value']
    )


def create_options(vals_list):
    '''
    Creates the options in the required format 
    Accepts List of tuple including name,value
    '''
    options = []
    for val in vals_list:
        options.append(
            {
                "text": {
                    "type": "plain_text",
                    "text": f"{val[0]}",
                },
                "value": val[1]
            }
        )
    return options


def create_block(text1, options = None, action = None, initial_option = None, text2 = None, type1 = None, block_id = None, type2 = 'section'):
    '''
    To generate block, 
    type ->
        For Dropdown send `static_select`
        For Radio send `radio_buttons`
    `initial_option` -> set the default option. -> {
        'value': 'value1',
        'text': 'dummy_text'
    }
    Options -> The options you want to display
    action -> the function to call on user interaction with this block
    '''
    # Block Pre Meta
    if type2 == 'section':
        elem_or_acc = 'accessory'
        text_or_labl = 'text'
    else:
        elem_or_acc = 'element'
        text_or_labl = 'label'
    data={
        'type': type2,
        text_or_labl: {
            'type': "plain_text",
            'text': text1
        }
    }
    if type1:
        data[elem_or_acc] =  {
            'type': type1,
            'options': options,
            'action_id': action,
        }
    if initial_option:
        data[elem_or_acc]['initial_option'] = {
            "value": initial_option['value'],
            "text": {
                "type": "plain_text",
                "text": initial_option['text']
            }
        }
    if type1 == 'static_select':
        data[elem_or_acc]['placeholder'] = {
            "type": "plain_text",
            "text": text2,
        }
    if block_id:
        data['block_id'] = block_id
    return data






# setting custom OOO reply shortcut
@app.shortcut("set_status_callback")
def open_modal(ack, shortcut, client):
    ack()
    print(shortcut)
    global user_id     
    user_id = shortcut["user"]["id"]
    print(user_id)
    client.views_open(
        trigger_id = shortcut["trigger_id"],
        view = {
            "type": "modal",
                "callback_id": "setting_status",
                "title": {"type": "plain_text", "text": "Set Default Message"},
                "close": {"type": "plain_text", "text": "Close"},
            "blocks": [
                    create_block(
                        '"Set the Message to be sent to the person"',
                        block_id = "description_block"
                    ),
                    {
                        "type": "divider",
                        "block_id": "divider_block"
                    },
                    create_block( 
                        "Select",
                        block_id = "check_radio_block",
                        options = create_options(
                            [
                                ("Set Default Message","value-0"),
                                ("Set Custom Message","value-1")
                            ]
                        ),
                        action = "add_update_radio_buttons_action",
                        type1 = 'radio_buttons'
                    )
                ]    

        }

    )

# when the user has selected the radio option 
@app.action("add_update_radio_buttons_action")
def update_modal(ack, body, client):
    ack()
    print(body)
    print(user_id)
    prev_blocks = body['view']['blocks'] # 0 > description, 1 > divider, 2 > radio, 3 > dropdown
    prev_blocks[2]['accessory']['initial_option'] = create_initial_options(body, 'check_radio_block', 'add_update_radio_buttons_action')
    prev_blocks.append(
        {
            "type": "input",
            "block_id": "issue_description",
            "element": {
                "type": "plain_text_input",
                "multiline": True,
                "action_id": "plain_text_input_action"
            },
            "label": {
                "type": "plain_text",
                "text": "Enter the Message",
                "emoji": True
            }
        }

        )
    choice = body['actions'][0]['selected_option']['value']
    if choice == 'value-0': # when the default text option is chosen 
        with open('default_text.txt', 'r') as fp:
            # here we read the default_text.txt and convert it to a dictionary
            # since the user is selecting the default text, the custom OOO reply, which is saved against his userId is deleted from the file
            # the updated dictionary is then converted to a string which is stored in final_str variable
                r = fp.read()
                dic = {}
                dic = json.loads(r)
                del dic[body["user"]["id"]]
                global final_str
                final_str = json.dumps(dic)

                

        with open('default_text.txt', 'w') as fp:
            # here we write the final_str which has the updated OOO replies
            fp.write(final_str)
        
    elif choice == 'value-1':
        print('reached inside elif')
        # the user has selected the custom reply option and is prompted to write the custom reply in input box 
        
        client.views_update(
            # Pass the view_id
            view_id=body["view"]["id"],
            # String that represents view state to protect against race conditions
            hash=body["view"]["hash"],
            # View payload with updated blocks
            view={
                "type": "modal",
                # View identifier
                "callback_id": "option_select",
                "title": {"type": "plain_text", "text": "Write"},
                "close": {"type": "plain_text", "text": "Close"},
                "submit": {"type": "plain_text", "text": "Submit"},
                "blocks": prev_blocks
            }
        )

# this is a global variable (l) used to read and write the default_text.txt
l=""        

# when the submit button is clicked 
@app.view("option_select")
def writeInFile(client, ack, body):
    ack()
    print("submit clicked--------")
    text = body['view']['state']['values']['issue_description']['plain_text_input_action']['value']
    
    print(text)
    
    global l # this is a global variable (l) used to read and write the default_text.txt

    

    try:
        # when the default_text.txt exists
        with open('default_text.txt', 'r') as fp:
            res={} # res is a dictionary used to store the key value pair of userId and his/her custom reply
            l = fp.read()
            print('before---', l)
            res = json.loads(l)
            res[user_id] = text
            l = json.dumps(res) # the res is dumped in a String variable l
    except:
        # when the default_text.txt doesn't exist
        
        res={} # res is a dictionary used to store the key value pair of userId and his/her custom reply
        res[user_id] = text
        l = json.dumps(res) # the res is dumped in a String variable l

    # writing the default_text.txt with the updated dictionary
    with open('default_text.txt', 'w') as f:
        print('after---', l)
        f.write(l)    





    
# final_str is the golbal variable used to manipulate the default_text.txt when the user status is changed 
final_str =""

# When selecting Out of Office, change presence to away
@app.event("user_status_changed")
def handle_user_status_changed_events(logger, event, context, client, body, ack, shortcut):
    ack()
    status = event["user"]["profile"]["status_text"]
    print('printing event:- ')
    print(event)
    #flag = 
    
    try:
        if status == "Out of Office":
            app.client.users_setPresence(
                token = context.user_token,
                presence = "away"
                )
            flag = 1
        else:
            with open('default_text.txt', 'r') as fp:
                r = fp.read() # reading the file
                dic = {} # dictionary used for holding the file in dictionary format
                dic = json.loads(r)
                del dic[event["user"]["id"]]
                
                # final_str is the golbal variable used to manipulate the default_text.txt when the user status is changed 
                global final_str
                final_str = json.dumps(dic) # dumping dic in final_str

            # writing the default_text.txt with final_str
            with open('default_text.txt', 'w') as fp:
                fp.write(final_str)

            
    except Exception as err:
        print(err)


    
    




## Comment out when creating flask app
# Start your app
if __name__ == "__main__":
    ## Socket Mode
    # SocketModeHandler(app, configur.get("config2","SLACK_APP_TOKEN")).start()
    ## HTTP Mode
    # Starts a web server for local development.
    app.start(port=int(os.environ.get("PORT", 3000)))
