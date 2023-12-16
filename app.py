#----------------------------------------------------------------------------#
# Help from Udacity's Chatgpt prompt attributed #
#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
import sys
import traceback
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form, FlaskForm, CSRFProtect
from wtforms import StringField, SelectField, SelectMultipleField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Optional, URL
from forms import VenueForm, ArtistForm, ShowForm
from sqlalchemy import func
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.dialects.postgresql import JSON

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:abc@localhost:5432/fyyur'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app,db)
moment = Moment(app)
app.config.from_object('config')

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime

def is_valid_genre(genre_id):
    return Genre.query.get(genre_id) is not None

def create_genres(selected_genres):
    """
    Create Genre objects based on the selected genre names.

    Args:
    - selected_genres: A list of selected genre names.

    Returns:
    - A list of Genre objects.
    """
    genres = []
    
    for genre_name in selected_genres:
        existing_genre = Genre.query.filter_by(name=genre_name).first()
        if existing_genre:
            genres.append(existing_genre)
        else:
            new_genre = Genre(name=genre_name)
            genres.append(new_genre)
            db.session.add(new_genre)
    
    return genres
#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

venue_genre = db.Table('venue_genre',
    db.Column('venue_id', db.Integer, db.ForeignKey('venues.id'), primary_key=True),
    db.Column('genre_id', db.Integer, db.ForeignKey('genres.id'), primary_key=True)
)

artist_genres = db.Table('artist_genres',
    db.Column('artist_id', db.Integer, db.ForeignKey('artists.id'), primary_key=True),
    db.Column('genre_id', db.Integer, db.ForeignKey('genres.id'), primary_key=True)
)


class Genre(db.Model):
    __tablename__ = 'genres'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    description = db.Column(db.String)
    venues = db.relationship('Venue', secondary=venue_genre, back_populates='genres')
    artists = db.relationship('Artist', secondary='artist_genres', back_populates='genres')

    def __repr__(self):
        return f'Genre {self.name}'
    
class City(db.Model):
    __tablename__ = 'cities'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)

    artists = db.relationship('Artist', back_populates='city', lazy=True)
    venues = db.relationship('Venue', back_populates='city', lazy=True)

    def __repr__(self):
        return f'City # {self.id}, Name {self.name}'

class Artist(db.Model):
    __tablename__ = 'artists'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id'), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    website_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120), nullable=True)
    seeking_venue = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String(500))
    image_link = db.Column(db.String(500))

    shows = db.relationship('Show', back_populates='artist', lazy=True)
    genres = db.relationship('Genre', secondary='artist_genres', back_populates='artists')

    city = db.relationship('City', back_populates='artists')

    def __repr__(self):
        return f'Artist # {self.id}, Name {self.name}'

class Show(db.Model):
    __tablename__ = 'shows'

    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('artists.id'), nullable=False)
    artist = db.relationship('Artist', back_populates='shows', lazy=True)
    venue_id = db.Column(db.Integer, db.ForeignKey('venues.id'), nullable=False)
    venues = db.relationship('Venue', back_populates='shows', lazy=True)
    start_time = db.Column(db.DateTime, nullable=False)
    venue = db.relationship('Venue', back_populates='shows', lazy=True)
    
    
    def __repr__(self):
        return f'<Show {self.id}, Artist {self.artist_id}, Venue {self.venue_id}>'

class Venue(db.Model):
    __tablename__ = 'venues'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey('cities.id'), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(120), nullable=True)
    website_link = db.Column(db.String(500), nullable=True)
    facebook_link = db.Column(db.String(120), nullable=True)
    image_link = db.Column(db.String(500), nullable=True)
    seeking_talent = db.Column(db.Boolean, default=True)
    seeking_description = db.Column(db.String(500), nullable=True)

    shows = db.relationship('Show', back_populates='venues', lazy=True)
    genres = db.relationship('Genre', secondary=venue_genre, back_populates='venues')
    city = db.relationship('City', back_populates='venues', lazy=True)

    def __repr__(self):
        return f'Venue # {self.id}, Name {self.name}'

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')

# Venues
# ----------------------------------------------------------------

@app.route('/venues')
def venues():
    data = []
    venues = Venue.query.all()
    locations = set()

    for venue in venues:
        locations.add((venue.city, venue.state))

    for location in locations:
        data.append({
            "city": location[0],
            "state": location[1],
            "venues": []
        })

    for venue in venues:
        num_upcoming_shows = 0
        shows = Show.query.filter_by(venue_id=venue.id).all()
        current_date = datetime.now()

        for show in shows:
            if show.start_time > current_date:
                num_upcoming_shows += 1

        for venue_location in data:
            if venue.state == venue_location['state'] and venue.city == venue_location['city']:
                venue_location['venues'].append({
                    "id": venue.id,
                    "name": venue.name,
                    "num_upcoming_shows": num_upcoming_shows,
                    "shows": shows  # Pass the shows information here
                })
    return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
    return redirect(url_for('search', search_term=request.form.get('search_term', '')))


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    venue = Venue.query.get(venue_id)
    shows = Show.query.filter_by(venue_id=venue_id).all()
    past_shows = []
    upcoming_shows = []
    current_time = datetime.now()

    for show in shows:
        data = {
            "artist_id": show.artist_id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": format_datetime(str(show.start_time))
        }
        if show.start_time > current_time:
            upcoming_shows.append(data)
        else:
            past_shows.append(data)

    data = {
        "id": venue.id,
        "name": venue.name,
        "genres": venue.genres,
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": venue.phone,
        "website": venue.website_link,
        "facebook_link": venue.facebook_link,
        "seeking_talent": venue.seeking_talent,
        "seeking_description": venue.seeking_description,
        "image_link": venue.image_link,
        "past_shows": past_shows,
        "upcoming_shows": upcoming_shows,
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows)
    }

    return render_template('pages/show_venue.html', venue=data)


# Create Venue
# ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

# /venues/create route
# /venues/create route
@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    form = VenueForm(request.form)
    print("Form Data:", form.data)

    if form.validate():
        try:
            # Check if the venue already exists in the session
            existing_venue = Venue.query.filter_by(name=form.name.data).first()

            if existing_venue:
                flash("Venue " + request.form["name"] + " already exists.")
                return redirect(url_for("index"))

            # Check if the city already exists in the session
            city_name = form.city.data
            state = form.state.data  # Get the state data from the form
            existing_city = City.query.filter_by(name=city_name, state=state).first()

            if existing_city:
                new_venue_city = existing_city
            else:
                new_city = City(name=city_name, state=state)  # Provide the state when creating a new city
                db.session.add(new_city)
                new_venue_city = new_city

            # Create Genre instances and add them to the venue's genres relationship
            genres_data = form.genres.data
            genres = create_genres(genres_data)

            new_venue = Venue(
                name=form.name.data,
                city=new_venue_city,
                state=form.state.data,
                address=form.address.data,
                phone=form.phone.data,
                image_link=form.image_link.data,
                website_link=form.website_link.data,
                seeking_description=form.seeking_description.data,
                facebook_link=form.facebook_link.data,
                seeking_talent=form.seeking_talent.data,
                genres=genres  # Assign the list of Genre objects to the venue's genres
            )

            db.session.add(new_venue)
            db.session.commit()
            flash("Venue " + request.form["name"] + " was successfully listed!")
        except Exception as e:
            print("Exception:", str(e))
            db.session.rollback()
            flash("An error occurred. Venue was not successfully listed.")
        finally:
            db.session.close()
    else:
        print("Form Data:", form.data)
        print("Form Errors:", form.errors)
        flash("An error occurred. Venue was not successfully listed. Please check the form inputs.")

    return redirect(url_for("index"))



#  Artists
#  ----------------------------------------------------------------


@app.route('/artists')
def artists():
    data = []

    artists = Artist.query.all()

    for artist in artists:
        data.append({
            "id": artist.id,
            "name": artist.name
        })

    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    return redirect(url_for('search', search_term=request.form.get('search_term', '')))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    artist = Artist.query.get(artist_id)
    shows = Show.query.filter_by(artist_id=artist_id).all()
    past_shows = []
    upcoming_shows = []
    current_time = datetime.now()

    for show in shows:
        data = {
            "venue_id": show.venue_id,
            "venue_name": show.venues.name,
            "venue_image_link": show.venue.image_link,
            "start_time": format_datetime(str(show.start_time))
        }
        if show.start_time > current_time:
            upcoming_shows.append(data)
        else:
            past_shows.append(data)

    data = {
        "id": artist.id,
        "name": artist.name,
        "genres": artist.genres,
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "facebook_link": artist.facebook_link,
        "image_link": artist.image_link,
        "past_shows": past_shows,
        "upcoming_shows": upcoming_shows,
        "past_shows_count": len(past_shows),
        "upcoming_shows_count": len(upcoming_shows)
    }

    return render_template('pages/show_artist.html', artist=data)


@app.route('/search', methods=['GET'])
def search():
    search_term = request.args.get('search_term', '')

    # Perform search for both venues and artists
    venues_result = Venue.query.filter(Venue.name.ilike(f'%{search_term}%')).all()
    artists_result = Artist.query.filter(Artist.name.ilike(f'%{search_term}%')).all()

    # Prepare the search results
    venues = [{
        "id": venue.id,
        "name": venue.name,
        "num_upcoming_shows": len(Show.query.filter(Show.venue_id == venue.id).filter(Show.start_time > datetime.now()).all())
    } for venue in venues_result]

    artists = [{
        "id": artist.id,
        "name": artist.name,
        "num_upcoming_shows": len(Show.query.filter(Show.artist_id == artist.id).filter(Show.start_time > datetime.now()).all())
    } for artist in artists_result]

    response = {
        "count": {
            "venues": len(venues),
            "artists": len(artists)
        },
        "data": {
            "venues": venues,
            "artists": artists
        }
    }

    return render_template('pages/search.html', results=response, search_term=search_term)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = Artist.query.get(artist_id)

    artist_data = {
        "id": artist.id,
        "name": artist.name,
        "genres": artist.genres,
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "facebook_link": artist.facebook_link,
        "image_link": artist.image_link
    }

    return render_template('forms/edit_artist.html', form=form, artist=artist_data)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    try:
        form = ArtistForm()

        artist = Artist.query.get(artist_id)
        artist.name = form.name.data
        artist.phone = form.phone.data
        artist.state = form.state.data
        artist.city = form.city.data
        artist.genres = form.genres.data
        artist.image_link = form.image_link.data
        artist.facebook_link = form.facebook_link.data

        db.session.commit()
        flash('The Artist ' + request.form['name'] + ' has been updated!')
    except:
        db.session.rollback()
        flash('An Error has occurred and the update was unsuccessful')
    finally:
        db.session.close()

    return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    venue = Venue.query.get(venue_id)
    form.genres.data = [(genre.id, genre.name) for genre in venue.genres]
    
    return render_template('forms/edit_venue.html', form=form, venue=venue)

# In edit_venue_submission:
@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    try:
        form = VenueForm()
        venue = Venue.query.get(venue_id)

        if not venue:
            flash('Venue not found!')
            return redirect(url_for('index'))

        if form.validate():
            venue.name = form.name.data
            venue.city = form.city.data
            venue.state = form.state.data
            venue.address = form.address.data
            venue.phone = form.phone.data
            venue.website_link = form.website_link.data
            venue.facebook_link = form.facebook_link.datacreate_artist_sub
            venue.image_link = form.image_link.data
            venue.seeking_talent = form.seeking_talent.data
            venue.seeking_description = form.seeking_description.data

            # Clear the existing genres and add the selected genres using the helper function
            venue.genres = create_genres(form.genres.data)

            db.session.commit()
            flash('Venue ' + venue.name + ' has been updated')
        else:
            flash('Validation error: Venue ' + venue.name + ' was not updated')

    except:
        db.session.rollback()
        flash('An error occurred while trying to update Venue ' + venue.name)
    finally:
        db.session.close()

    return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------
@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    form = ArtistForm(request.form)
    print("Form Data:", form.data)

    if form.validate():
        try:
            # Check if the artist already exists in the session
            existing_artist = Artist.query.filter_by(name=form.name.data).first()

            if existing_artist:
                flash("Artist " + request.form["name"] + " already exists.")
                return redirect(url_for("index"))

            # Check if the city already exists in the session
            city_name = form.city.data
            state_name = form.state.data  # Get the state from the form
            existing_city = City.query.filter_by(name=city_name, state=state_name).first()

            if existing_city:
                new_artist_city = existing_city
            else:
                new_city = City(name=city_name, state=state_name)  # Provide the state
                db.session.add(new_city)
                new_artist_city = new_city

            new_artist = Artist(
                name=form.name.data,
                city=new_artist_city,
                state=form.state.data,
                phone=form.phone.data,
                image_link=form.image_link.data,
                facebook_link=form.facebook_link.data,
                website_link=form.website_link.data,
                seeking_venue=form.seeking_venue.data,
                seeking_description=form.seeking_description.data
            )

            # Create Genre instances and add them to the artist's genres relationship
            genres_data = form.genres.data
            genres = []

            for genre_name in genres_data:
                existing_genre = Genre.query.filter_by(name=genre_name).first()
                if existing_genre:
                    genres.append(existing_genre)
                else:
                    new_genre = Genre(name=genre_name)
                    genres.append(new_genre)
                    db.session.add(new_genre)

            new_artist.genres.extend(genres)
            db.session.add(new_artist)
            db.session.commit()
            flash("Artist " + request.form["name"] + " was successfully listed!")
        except Exception as e:
            print("Exception:", str(e))
            db.session.rollback()
            flash("An error occurred. Artist was not successfully listed.")
        finally:
            db.session.close()
    else:
        print("Form Data:", form.data)
        print("Form Errors:", form.errors)
        flash("An error occurred. Artist was not successfully listed. Please check the form inputs.")

    return redirect(url_for("index"))



@app.route('/artists/<artist_id>', methods=['GET'])
def delete_artist(artist_id):
    try:
        artist = Artist.query.get(artist_id)
        artist_name = artist.name

        db.session.delete(artist)
        db.session.commit()

        flash('Artist ' + artist_name + ' was successfully deleted.')
    except:
        db.session.rollback()
        flash('An error occurred. Artist ' + artist_name + ' was not deleted.')
    finally:
        db.session.close()

    return redirect(url_for('index'))

# Shows
# ----------------------------------------------------------------

@app.route('/shows')
def shows():
    shows = Show.query.order_by(db.desc(Show.start_time))
    data = []

    for show in shows:
        data.append({
            "venue_id": show.venue_id,
            "venue_name": show.venues.name,  # Access venue name through the 'venues' relationship
            "artist_id": show.artist_id,
            "artist_name": show.artist.name,  # Access artist name through the 'artist' relationship
            "artist_image_link": show.artist.image_link,
            "start_time": format_datetime(str(show.start_time))
        })

    return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)

from flask import flash

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    form = ShowForm(request.form)
    
    if form.validate():
        try:
            new_show = Show(
                artist_id=form.artist_id.data,
                venue_id=form.venue_id.data,
                start_time=form.start_time.data
            )
            db.session.add(new_show)
            db.session.commit()
            flash('Show was successfully listed!', 'success')
        except Exception as e:
            db.session.rollback()
            print(str(e))
            flash('An error occurred while listing the show. Please try again.', 'danger')
        finally:
            db.session.close()
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Error in {getattr(form, field).label.text}: {error}', 'danger')

        flash('Show was not successfully listed. Please fix the errors below.', 'danger')

    return redirect(url_for("index"))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500

if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# Launch.
# ----------------------------------------------------------------

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
