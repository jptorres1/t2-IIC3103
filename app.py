from flask import request, Flask, Response, jsonify, json
from flask_sqlalchemy import SQLAlchemy
from base64 import b64encode
from sqlalchemy.exc import IntegrityError
from psycopg2.errors import UniqueViolation, ForeignKeyViolation

app = Flask(__name__)

ENV = 'prod'

if ENV == 'dev':
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost/'
else:
    app.debug = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://dzdedwlxiblypb:3e6aa941ce957715b6511a6a3f86e60264a6177f1b6d3900b67c9dad23e566c7@ec2-54-224-120-186.compute-1.amazonaws.com:5432/dbebmpc1jp2ota'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Artist(db.Model):
    __tablename__ = 'artist'
    id = db.Column(db.String(22), primary_key=True)
    name = db.Column(db.String(200), unique=True)
    age = db.Column(db.Integer)
    albums= db.relationship('Album', backref='artist', lazy=True, cascade="all, delete-orphan")
    tracks = db.relationship('Track', backref='artist', lazy=True, cascade="all, delete-orphan")
    albums_url = db.Column(db.String(200), unique=True)
    tracks_url = db.Column(db.String(200), unique=True)
    self_url = db.Column(db.String(200), unique=True)

    def __init__(self, id, name, age):
        self.id = id
        self.self_url = f'https://espotifai.herokuapp.com/artists/{id}'
        self.name = name
        self.age = age
        self.albums_url = self.self_url + '/albums'
        self.tracks_url = self.self_url + '/tracks'

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            'age': self.age,
            'albums': self.albums_url,
            'tracks': self.tracks_url,
            'self': self.self_url
        }




class Album(db.Model):
    __tablename__ = 'album'
    id = db.Column(db.String(22), primary_key=True)
    name = db.Column(db.String(200))
    genre = db.Column(db.String(200))
    artist_id = db.Column(db.String(22), db.ForeignKey('artist.id'),
        nullable=False)
    tracks = db.relationship('Track', backref='album', lazy=True, cascade="all, delete-orphan")
    artist_url = db.Column(db.String(200))
    tracks_url = db.Column(db.String(200))
    self_url = db.Column(db.String(200), unique=True)


    def __init__(self, id, name, genre, artist_id):
        self.id = id
        self.self_url = f'https://espotifai.herokuapp.com/albums/{id}'
        self.name = name
        self.genre = genre
        self.artist_id = artist_id
        self.artist_url = f'https://espotifai.herokuapp.com/artists/{artist_id}'
        self.tracks_url = self.self_url + f'/tracks'

    def serialize(self):
        return {
            'id': self.id,
            'artist_id': self.artist_id,
            'name': self.name,
            'genre': self.genre,
            'artist': self.artist_url,
            'tracks': self.tracks_url,
            'self': self.self_url
        }




class Track(db.Model):
    __tablename__ = 'track'
    id = db.Column(db.String(22), primary_key=True)
    name = db.Column(db.String(200))
    duration = db.Column(db.Float)
    times_played = db.Column(db.Integer)
    artist_id = db.Column(db.String(22), db.ForeignKey('artist.id'),
        nullable=False)
    album_id = db.Column(db.String(22), db.ForeignKey('album.id'),
        nullable=False)
    artist_url = db.Column(db.String(200))
    album_url = db.Column(db.String(200))
    self_url = db.Column(db.String(200), unique=True)

    def __init__(self, id, name, duration, artist_id, album_id):
        self.id = id
        self.self_url = f'https://espotifai.herokuapp.com/tracks/{id}'
        self.name = name
        self.duration = duration
        self.times_played = 0
        self.artist_id = artist_id
        self.album_id = album_id
        self.artist_url = f'https://espotifai.herokuapp.com/artists/{artist_id}'
        self.album_url = f'https://espotifai.herokuapp.com/albums/{album_id}'

    def play(self):
        self.times_played += 1

    def serialize(self):
        return {
            'id': self.id,
            'album_id': self.album_id,
            'name': self.name,
            'duration': self.duration,
            'times_played': self.times_played,
            'artist': self.artist_url,
            'album': self.album_url,
            'self': self.self_url
        }



# ARTIST_KEYS = ['name', 'age']
# ALBUM_KEYS = ['name', 'genre']
# TRACK_KEYS = ['name', 'duration', 'times_played']

# POST
@app.route('/artists', methods=['POST'])
def post_artist():
    data = dict(request.args)
    name = data.get('name')
    age = data.get('age')

    try:
        if (name is None) or (age is None):
            return Response(status=400)
        age = int(age)
        if (type(age) is not int):
            return Response(status=400)
        _id = b64encode(name.encode()).decode('utf-8')[:22]
        artist = Artist(id=_id, name=name, age=age)
        db.session.add(artist)
        db.session.commit()
        return Response(status=201)

    except ValueError:
        return Response(status=400)
    except IntegrityError as e:
        db.session.rollback()
        if isinstance(e.orig, UniqueViolation):
            artist = Artist.query.filter_by(id=_id).first()
            return Response(status=409, response=json.dumps(artist.serialize()), mimetype='json')


@app.route('/artists/<string:artist_id>/albums', methods=['POST'])
def post_album(artist_id):
    data = dict(request.args)
    name = data.get('name')
    genre = data.get('genre')
    if (name is None) or (genre is None):
        return Response(status=400)
    _id = b64encode(f'{name}:{artist_id}'.encode()).decode('utf-8')[:22]

    try:
        album = Album(id=_id, name=name, genre=genre, artist_id=artist_id)
        db.session.add(album)
        db.session.commit()
        return Response(status=201)

    except IntegrityError as e:
        db.session.rollback()
        if isinstance(e.orig, UniqueViolation):
            album = Album.query.filter_by(id=_id).first()
            return Response(status=409, response=json.dumps(album.serialize()), mimetype='json')
        elif isinstance(e.orig, ForeignKeyViolation):
            return Response(status=422)


@app.route('/albums/<string:album_id>/tracks', methods=['POST'])
def post_track(album_id):
    data = dict(request.args)
    name = data.get('name')
    duration = data.get('duration')
    if (name is None) or (duration is None):
        return Response(status=400)
    _id = b64encode(f'{name}:{album_id}'.encode()).decode('utf-8')[:22]

    try:
        duration = float(duration)
        artist_id = Album.query.filter_by(id=album_id).first().artist_id
        track = Track(id=_id, name=name, duration=duration, 
                        artist_id = artist_id, album_id=album_id)
        db.session.add(track)
        db.session.commit()
        return Response(status=201)

    except ValueError:
        return Response(status=400)
    except IntegrityError as e:
        db.session.rollback()
        if isinstance(e.orig, UniqueViolation):
            track = Track.query.filter_by(id=_id).first()
            return Response(status=409, response=json.dumps(track.serialize()), mimetype='json')
        elif isinstance(e.orig, ForeignKeyViolation):
            return Response(status=422)
    



# GET
@app.route('/artists', methods=['GET'])
def artists():
    artists_all = Artist.query.all()
    if artists_all == []:
        return Response(status=404)
    return jsonify([a.serialize() for a in artists_all])
   

@app.route('/albums', methods=['GET'])
def albums():
    albums_all = Album.query.all()
    if albums_all == []:
        return Response(status=404)
    return jsonify([a.serialize() for a in albums_all])


@app.route('/tracks', methods=['GET'])
def tracks():
    tracks_all = Track.query.all()
    if tracks_all == []:
        return Response(status=404)
    return jsonify([t.serialize() for t in tracks_all])


@app.route('/artists/<string:artist_id>', methods=['GET'])
def artist(artist_id):
    artist = Artist.query.filter_by(id=artist_id).first_or_404()
    return jsonify(artist.serialize())


@app.route('/artists/<string:artist_id>/albums', methods=['GET'])
def artist_albums(artist_id):
    albums_all = Album.query.filter_by(artist_id=artist_id).all()
    if albums_all == []:
        return Response(status=404)
    return jsonify([a.serialize() for a in albums_all])


@app.route('/artists/<string:artist_id>/tracks', methods=['GET'])
def artist_tracks(artist_id):
    tracks_all = Track.query.filter_by(artist_id=artist_id).all()
    if tracks_all == []:
        return Response(status=404)
    return jsonify([t.serialize() for t in tracks_all])


@app.route('/albums/<string:album_id>', methods=['GET'])
def album(album_id):
    album = Album.query.filter_by(id=album_id).first_or_404()
    return jsonify(album.serialize())


@app.route('/albums/<string:album_id>/tracks', methods=['GET'])
def album_tracks(album_id):
    tracks_all = Track.query.filter_by(album_id=album_id).all()
    if tracks_all == []:
        return Response(status=404)
    return jsonify([t.serialize() for t in tracks_all])


@app.route('/tracks/<string:track_id>', methods=['GET'])
def track(track_id):
    track = Track.query.filter_by(id=track_id).first_or_404()
    return jsonify(track.serialize())



# PUT
@app.route('/artists/<string:artist_id>/albums/play', methods=['PUT'])
def play_artists(artist_id):
    tracks_all = Track.query.filter_by(artist_id=artist_id).all()
    if tracks_all == []:
        return Response(status=404)
    for track in tracks_all:
        track.play()
    db.session.commit()
    return Response(status=200)


@app.route('/albums/<string:album_id>/tracks/play', methods=['PUT'])
def play_album(album_id):
    tracks_all = Track.query.filter_by(album_id=album_id).all()
    if tracks_all == []:
        return Response(status=404)
    for track in tracks_all:
        track.play()
    db.session.commit()
    return Response(status=200)


@app.route('/tracks/<string:track_id>/play', methods=['PUT'])
def play_track(track_id):
    track = Track.query.filter_by(id=track_id).first_or_404()
    track.play()
    db.session.commit()
    return Response(status=200)



#DELETE
@app.route('/artists/<string:artist_id>', methods=['DELETE'])
def delete_artist(artist_id):
    artist = Artist.query.filter_by(id=artist_id).first_or_404()
    db.session.delete(artist)
    db.session.commit()
    return Response(status=204)


@app.route('/albums/<string:album_id>', methods=['DELETE'])
def delete_album(album_id):
    album = Album.query.filter_by(id=album_id).first_or_404()
    db.session.delete(album)
    db.session.commit()
    return Response(status=204)


@app.route('/tracks/<string:track_id>', methods=['DELETE'])
def delete_track(track_id):
    track = Track.query.filter_by(id=track_id).first_or_404()
    db.session.delete(track)
    db.session.commit()
    return Response(status=204)



if __name__ == '__main__':
    app.run()