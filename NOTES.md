##

Test connection to sensor board:  wget -O - 192.168.1.36
-or- wget -qO- 192.168.1.36

##

Run docker binding port 80 to container's 8080: docker run -p 80:8080 weather-html

##

Have docker inspect a volume to locate data files: docker volume inspect sql2025data

##

python3 -m venv venv
source venv/bin/activate

