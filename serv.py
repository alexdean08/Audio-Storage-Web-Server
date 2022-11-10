from flask import Flask, request, send_from_directory
from tinytag import TinyTag
import os
import glob
import magic
import json
app = Flask(__name__)

@app.route('/')
def main_call():
    return "Hello"

# stores raw audio data in 'files/'
# e.g. "curl -X POST --data-binary @sound.wav http://localhost/post"           <-- DOES NOT store with the name of file
@app.route('/post', methods=['POST'])
def submit_file_binary():

    if request.method == 'POST':
        
        # because it is raw audio data, the file name can't be stored with it, so create a new name for the file
        temp_file_num = 1+len([f for f in os.listdir('files/')])
        temp_file_name = 'files/temp'+str(temp_file_num)

        # opens a temporary file and writes the binary sound waves into it
        temp_file = open(temp_file_name, 'wb')
        temp_file.write(request.stream.read())
        temp_file.close()

        # gets the file type and audio type
        file_type, audio_type = magic.from_file(temp_file_name, mime=True).split('/')
        

        # if it isn't audio, return an error, otherwise save the file as the correct audio format
        if file_type != 'audio':
            os.remove(temp_file_name)
            return json.dumps('invalid filetype')
        
        audios = {'mpeg':'.mp3', 'x-wav':'.wav', 'x-m4a':'.m4a', 'x-flac':'.flac', 'x-hx-aac-adts':'.aac', 'x-aiff':'.aiff'}

        # in case I missed a certain audio file type
        try:
            os.rename(temp_file_name, temp_file_name+audios[audio_type])
        except:
            return json.dumps('successfully saved file, but unexpected audio type ' + audio_type)

        return json.dumps('successfully saved file ' + temp_file_name+audios[audio_type])

    return json.dumps('requires POST command')


# stores audio file in 'files/'
# e.g. "curl -X POST -F file=@sound.wav http://localhost/post-file"                 <-- DOES store with the name of file
@app.route('/post-file', methods=['POST'])
def submit_file():

    if request.method == 'POST':

        #requires file as input
        if len(request.files) > 0:

            r_files = request.files
            
            # goes through the file to ensure they are all audio files
            for f in r_files:
                file_type = ''
                for c in magic.from_file(request.files[f].filename, mime=True):
                    if c == '/':
                        break
                    file_type += c

                # if file isn't audio it returns an invalid file type
                if file_type != 'audio':
                    return json.dumps('invalid file type for ' + request.files[f].filename)
                
            # goes through and stores the files
            for f in r_files:
                request.files[f].save(f'files/{r_files[f].filename}')

            return json.dumps('file saved with name preserved!')
        
        return json.dumps('no file submitted')
    
    return json.dumps('requires POST command')
            
# better way to store data would be by connecting a database to this
# more secure and doesn't rely on a file system necessarily


# downloads audio file
# e.g. "curl http://localhost/download?name=myfile.wav"
@app.route('/download')
def download():

    # if file is present in 'files/', download. Otherwise 'invalid name for file'
    file_name = request.args.get('name')
    if file_name not in [f for f in os.listdir('files/')]:
        return (json.dumps('invalid name for file'), 400)
        return json.dumps('invalid name for file')
    
    return send_from_directory('files/', file_name)


# gets metadata of audio file
def get_file_info(f):
    metadata = dict()
    metadata['artist'] = TinyTag.get(f).artist
    metadata['album'] = TinyTag.get(f).album
    metadata['genre'] = TinyTag.get(f).genre
    metadata['year'] = TinyTag.get(f).year
    metadata['duration'] = TinyTag.get(f).duration
    return metadata


# lists all files based on a multitude of parameters

# Everything that can filter the list:
# maxduration, minduration, artist, genre, album, year, or none of them
# e.g. "curl http://localhost/list?maxduration=300" or "curl 'http://localhost/list?maxduration=300&minduration=1' "
@app.route('/list')
def list_files():

    file_dict = dict()
    for f in os.listdir('files/'):
        file_dict[f] = get_file_info('files/'+f)

    # if no filter parameters, return full list of files
    if len(request.args) == 0:
        return json.dumps(file_dict)

    # filter down the list based on the parameters
    total_files = set(os.listdir('files/'))
    original_files = set(os.listdir('files/'))
    for arg in request.args:
        if arg == 'maxduration':
            total_files = total_files - (total_files - set([f for f in os.listdir('files/') if TinyTag.get('files/'+f).duration <= int(request.args.get('maxduration'))]))
        elif arg == 'minduration':
            total_files = total_files - (total_files - set([f for f in os.listdir('files/') if TinyTag.get('files/'+f).duration >= int(request.args.get('minduration'))]))
        elif arg == 'artist':
            total_files = total_files - (total_files - set([f for f in os.listdir('files/') if TinyTag.get('files/'+f).artist == request.args.get('artist')]))
        elif arg == 'genre':
            total_files = total_files - (total_files - set([f for f in os.listdir('files/') if TinyTag.get('files/'+f).genre == request.args.get('genre')]))
        elif arg == 'album':
            total_files = total_files - (total_files - set([f for f in os.listdir('files/') if TinyTag.get('files/'+f).album == request.args.get('album')]))
        elif arg == 'year':
            total_file = total_files - (total_files - set([f for f in os.listdir('files/') if TinyTag.get('files/'+f).year == request.args.get('year')]))
        else:
            return json.dumps('invalid argument \''+arg+'\'')
    
    # pop out the files that didn't make the cut
    for p in original_files - total_files:
        file_dict.pop(p)

    # return the filtered list of file names
    return json.dumps(file_dict)
    

# returns metadata of file
# duration, artist, genre, album, year
@app.route('/info')
def file_info():
    if request.args.get('name') == None or request.args.get('name') not in [f for f in os.listdir('files/')]:
        return json.dumps('invalid \'name\' argument')

    return json.dumps(get_file_info('files/' + request.args.get('name')))

    



if __name__ == '__main__':
    fs = glob.glob('files/*')
    for f in fs:
        os.remove(f)
    app.run(debug=True, port=80)
    #app.run(debug=True, port=80, ssl_context='adhoc')
    # ^^^ doesn't let me do ssl on WSL 2. So, can't do https on WSL 2.
