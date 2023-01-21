curl -1sLf \
  'https://repositories.timber.io/public/vector/cfg/setup/bash.deb.sh' \
  | sudo -n -E bash
echo -e "Package: vector\nPin: version 0.26.0-1\nPin-Priority: 999" \
  > /etc/apt/preferences.d/vector && apt-get install vector=0.26.0-1
wget -O ->> /etc/vector/vector.toml \
    https://logtail.com/vector-toml/ubuntu/R6xznP5wmFLoKq5it6FnEmWw
usermod -a -G mysql vector 2> /dev/null || echo "skipping mysql"; \
  (usermod -a -G mongodb vector && chmod g+r /var/log/mongodb/mongod.log) 2> /dev/null || echo "skipping mongodb"; \
  usermod -a -G docker vector 2> /dev/null || echo "skipping docker"
systemctl restart vector
systemctl status vector