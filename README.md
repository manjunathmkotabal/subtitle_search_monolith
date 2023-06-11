# subtitle_search_cloud

Upload videos with embedded subtitles and search for vides with phrases

## Description

This project is a video search application that allows users to search for videos based on keyword queries. The application retrieves videos from an S3 bucket and provides a search interface where users can enter keywords. The application then queries subtitles associated with the videos to find matches for the given keywords.

## Getting Started

### Dependencies

* Django , celery 
* Linux OS

### Installing

* git clone this repo and replace all aws creadential wherever necessary.


### Executing program

* How to run the program
* install dependencies by running
```
pip install -r requirements.txt
```
* start celery log level worker for performing tasks
```
celery -A videouploader worker -l info
```
* make migrations 
```
python manage.py makemigrations
python manage.py migrate
```
* Start the server by running 
```
python manage.py runserver
```
then visit - (http://127.0.0.1:8000/)

* for creating admin credentials run
```
python manage.py createsuperuser
```
enter credentials 

then visit - (http://127.0.0.1:8000/)

## Help

* if you find any errors, feel free to contact me

## Authors


ex. Manjunath Kotabal 
ex. [@manjukotabal](https://twitter.com/manjukotabal)

## Version History

* 0.1
    * Various bug fixes and optimizations
    * See [commit change]() or See [release history]()
* 0.1
    * Initial Release

## License

This project is licensed under the MIT License - see the LICENSE.md file for details

## Acknowledgments

Inspiration, code snippets, etc.
* [Priyanshu Gupta](https://www.youtube.com/@PriyanshuGuptaOfficial)
* [ecowiser](https://wiser.eco/)

