# Imports
import socket
from socket import gaierror
from flask import *
from flask_cors import CORS, cross_origin
import paramiko
import json
import io
import codecs

# Flask setup
app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

# Private key files
NAS_EXPAT = """REDACTED"""
EXPAT_RSA = """REDACTED"""


def getURL(x):
    if x == "ll":
        returnURL = "REDACTED"
    elif x == "ak":
        returnURL = "REDACTED"
    else:
        returnURL = "REDACTED"
    return returnURL


def returnCode(ip, password1, password2, cdn):
    # Initialise values
    exception = ""
    output = ""
    private_key1 = None
    private_key2 = None
    NUMBER_OF_KEYS = 2;

    # Initialise private key 1
    private_key_file1 = io.StringIO()
    private_key_file1.write(NAS_EXPAT)
    private_key_file1.seek(0)

    # Attempt to unlock private key 1 using passphrase 1
    try:
        private_key1 = paramiko.RSAKey.from_private_key(private_key_file1, password1)
    except paramiko.ssh_exception.SSHException:
        pass

    # Initialise private key 2
    private_key_file2 = io.StringIO()
    private_key_file2.write(EXPAT_RSA)
    private_key_file2.seek(0)

    # Attempt to unlock private key 2 using passphrase 2
    try:
        private_key2 = paramiko.RSAKey.from_private_key(private_key_file2, password2)
    except paramiko.ssh_exception.SSHException:
        pass

    # Append unlocked keys to list
    keylist = []
    if private_key1 != None:
        keylist.append(private_key1)
    if private_key2 != None:
        keylist.append(private_key2)

    # Initialise SSH client
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Check if given IP is in IP format
    try:
        socket.inet_aton(ip)
        pass
    except socket.error:
        exception = "ipErr"

    # Set localErr if using a local IP
    if ip == "127.0.0.1" or ip == "localhost":
        exception = "localErr"

    # This is where the fun begins
    if exception != "localErr" and exception != "ipErr":
        # Run for every key, including invalid ones
        for i in range(0, NUMBER_OF_KEYS):
            try:
                # Connect to client
                client.connect(ip, username="root", pkey=keylist[i], timeout=2)
                # Run GET request on getURL
                stdin, stdout, stderr = client.exec_command('wget ' + getURL(cdn))

                # Loop for lines of GET return data
                wgetindex = 0
                for line in stderr:
                    wgetindex += 1
                    if wgetindex == 4:
                        output = line

                # If empty, GET didn't work, so try cURL instead
                if output == "":
                    stdin, stdout, stderr = client.exec_command("curl -I " + getURL(cdn))
                    for line in stdout:
                        output += line

                # If GET did work, scrape the response code
                else:
                    output = output.split("response... ", 1)[1]
                    output = output[:3]
                    exception = ""
                break

            # Things which could go wrong include:
            except paramiko.ssh_exception.AuthenticationException:
                # Not having the right private key
                exception = "authErr"
            except TimeoutError:
                # Timing out (usually from an invalid IP)
                exception = "timeoutErr"
            except socket.timeout as e:
                # Timing out (but from another module)
                exception = "timeoutErr"
            except gaierror:
                # Having an invalid IP
                exception = "ipErr"
            except paramiko.ssh_exception.NoValidConnectionsError:
                # Having an invalid IP (but from another module)
                exception = "ipErr"
            except IndexError:
                # Having an incorrect passphrase
                if exception != "ipErr":
                    exception = "phraseErr"

    # If the 'try' worked on either attempt
    if output != "":
        # Remove the exception
        exception = ""
    # If there is still an exception
    if exception != "":
        # Set the output to the exception
        output = exception

    return output


@app.route('/')
@cross_origin()
def load_webpage():
    # Read contents of index.html file
    webpage = codecs.open("index.html", 'r')
    loadedpage = webpage.read()
    # Return those contents to be written the DOM
    return loadedpage


@app.route('/post', methods=["POST"])
@cross_origin()
def postFunc():
    # Load, trim, and JSONify POST data
    reqData = str(request.data)
    reqData = reqData[2:len(reqData) - 1]
    reqData = json.loads(reqData)

    # Send off the POST data to be run, and it either returns a response code or an error message
    return returnCode(reqData["ip"], reqData["pass1"], reqData["pass2"], reqData["cdn"]), 200


if __name__ == '__main__':
    app.run()
