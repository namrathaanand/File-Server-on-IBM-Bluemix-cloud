from flask import Flask
from flask import render_template, request
import swiftclient
import os
import pyDes
import urllib2

app=Flask(__name__)


#credentials used to login
auth_url = "https://identity.open.softlayer.com/v3" #add "/v3" at the ending of URL
password = "your password"
project_id = "your project id"
user_id = "your user id"
region_name = "dallas"


#making the connection
conn = swiftclient.Connection(key=password, authurl=auth_url, auth_version='3', os_options={"project_id": project_id, "user_id": user_id, "region_name": region_name})
print "Connection successful"


#creating a container(i.e. folder) to put files in
cont_name = "new-container"
conn.put_container(cont_name)
print "Container %s created successfully." %cont_name


#Key for encryption and decryption
from pyDes import *
k = des("DESCRYPT", CBC, "\0\0\0\0\0\0\0\0", pad=None, padmode=PAD_PKCS5)
#"DESCRYPT" id the passcode and it can be any 8 byte value


#landing function
@app.route('/')
def index():
    return render_template("index.html")

#upload function
@app.route('/upload')
def upload():

    file_name=request.args.get('file')

    #making the static/input folder act as server folder in application folder
    filepath='static/input/'+file_name

    #renaming file before uploading onto bluemix after encryption
    encrypt_filename = "Encrypted_" + file_name

    ##Encyption

    #checking if file is from server folder
    try:
        f = open(filepath, "rb+")
        data = f.read()
        f.close()
    except:
        error = "The file you have selected is not in the input folder."
        return render_template("index.html", output2=error)
    else:
        d = k.encrypt(data)
        f = open(encrypt_filename, "wb+")
        f.write(d)
        f.close()

        ##Uploading an existing file

        with open(encrypt_filename, 'r') as upload_file:
            conn.put_object(cont_name, encrypt_filename, contents=upload_file.read())

        ##Delete unwanted file
        os.remove(encrypt_filename)
        print 'unwanted file deleted!'

        ##Success message
        return 'File uploaded Successfully!'


#download function
@app.route('/download')
def download():
    file_name = request.args.get("filename")
    encrypt_filename = "Encrypted_" + file_name

    #saves files into the output folder in application folder
    filepath = 'static/output/' + file_name

    ## Downloading a file
    try:
        obj = conn.get_object(cont_name, encrypt_filename)

    except:
        error='Filename is incorrect or the file does not exist on Bluemix. Try again'
        return render_template('index.html',output1=error)

    ## Decrypting a file

    filebytes = obj[1]

    # print filebytes
    print 'decrypting'
    filecontents = k.decrypt(filebytes)

    # print filecontents
    with open(filepath, 'w') as download_file:
        download_file.write(filecontents)
    return 'File Downloaded Successfully!'


#function for listing files (i.e objects) in all the containers belonging to the current user account
@app.route('/list')
def list():
    l = []
    for container in conn.get_account()[1]:
        for obj in conn.get_container(container['name'])[1]:
            container_name=container['name']
            name = obj['name']
            size = obj['bytes']
            date = obj['last_modified']
            l.append((container_name, name, size, date))
    if not l:
        return 'There are no files on Bluemix'
    else:
        print 'l exists'
        return render_template('list.html', files=l)



#delete file function
@app.route('/delete')
def delete():
    file_name=request.args.get('filename')
    encrypt_filename = "Encrypted_" + file_name
    try:
        f = conn.delete_object(cont_name, encrypt_filename)
    except:
        error='Filename is incorrect or the file does not exist on Bluemix. Try again'
        return render_template('index.html',output=error)
    else:
        return 'The file is deleted from Bluemix'


#Exit function
@app.route('/exit')
def exit():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return 'You have now exited the application.'

#running application on 127.0.0.1
if __name__ == '__main__':
    app.run(port=5000,debug=True)