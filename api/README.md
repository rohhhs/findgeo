# Documentation of API usage .

```uvicorn api.auth_api:app --reload --port 8000```

## Fast API endpoints . 
./api/auth/
./api/auth/read
./api/auth/write 

### Programm requirements : 

1. Authentificate user in programm 
1. 1. Create new user and set encrypted password within username . Use only unique username . ( ./api/encryption/password.py encryptPassword -> saveUser -> ./api/encryption/token.py -> encodeAccount)
1. 2. Verify password and username (./api/encryption/password.py findUser -> verifyPassword -> ./api/encryption/token.py -> encodeAccount)
1. 3. Verify token (./api/encryption/token.py -> checkToken (./api/encryption/token.py decodeAccount -> ./api/encryption/password.py findUser) )

2. Load data for search 
2. 1. Load account data name , surname , orders , requests etc ... (./api/load-account -> ./api/encryption/token.py checkToken -> ./api/form_table/formdata readDataBase (read database from path ./asset/data/account/data.csv) )
2. 1. 1. UNDONE . Save new account data .
2. 1. 2. UNDONE . Update account data with request .
2. 2. Load image to identify address and object .
2. 2. 0. Find similar images with locations . 
2. 2. 1. Take latitude and longitude of similar images and list locations nearly latitude and longitude . 
2. 2. 1. 1. List locations from closest to farest to display on webpage .  
2. 2. 2. Identify object on the image to display objects on image on webpage . 
2. 2. Load address , latitude and logitude and other options as time period , camera of image , quality of an image .
2. 2. 0. Load all camera from data table by key value "camera" , "date" , "image_quality" to display in select option . 
2. 2. 1. Find images with similar geolocation , if latitude and longitude is provided to list on web page .
2. 2. 2. Find geolocation , if address provided and 2.2.1. find images close to geolocation to list on webpage .   
2. 2. 3. If latitude and longitude provided with address , find address geolocation and list closest images to address & geolocation . 

3. Load data for gallery .
3. 1. Load all data images from data table , up to 20 and button to load more and load each time more saving cache position of loaded images . 
3. 2. Load data from database : load_image_urls , image_object , address , coordinates (extend database and save with different name . 

4. Operations - download database , specify column to be downloaded , create database with certain columns if was not . (./api/form_table/init.py formDataBase -> JavaScript upload from path )

5. Operations - upload archive from website to other webpage files . 

6. Integration . Connect uploading process with API , object-by-object

### Locations to load data

./ - none

./auth (login) - ./api/encryption/password.py findUser -> verifyPassword -> ./api/encryption/token.py -> encodeAccount 
./auth (register) - ./api/encryption/password.py encryptPassword -> saveUser -> ./api/encryption/token.py -> encodeAccount

./office (read) - ./api/encryption/token.py checkToken -> ./api/form_table/formdata.py readDataBase
./office (edit) - ./api/encryption/token.py checkToken -> ./api/form_table/writedata.py writeDataBase

./search (read image) - ./api/encryption/token.py checkToken -> ./api/identify/init.py findGeo -> ./api/form_table/formdata.py readDataBase
./search (read table) - ./api/encryption/token.py checkToken -> ./api/identify/init.py findGeo -> ./api/form_table/formdata.py readDataBase

./gallery - ./api/encryption/token.py checkToken -> ./api/form_table/formdata.py readDataBase
./gallery/table - ./api/encryption/token.py checkToken -> ./api/form_table/formdata.py readDataBase

./operation - none
./operation/download - ./api/encryption/token.py checkToken -> ./api/form_table/init.py formDataBase
./operation/integrate - ./api/encryption/token.py checkToken -> ./api/form_table/writedata.py writeDataBase
./operation/upload - ./api/encryption/token.py checkToken -> ./api/extend_data/init.py createNewTable

./other - none

# TODO 

./api/form_table/writedata.py writeDataBase (./operation/integrate)
./api/form_table/writedata.py editRowDataBase (./office)
./api/identify/init.py findGeo (./search)
./api/extend_data/init.py createNewTable (./operation/upload)