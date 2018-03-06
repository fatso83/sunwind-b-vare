Sunwind B-varevarsler
========================

> Henter listen av b-varer hos sunwind og varsler om nyheter

## Installasjon

    #Clone the repository 
    git clone https://github.com/fatso83/sunwind-b-vare

    cd sunwind
    
    # install the requirements
    pip install -r requirements.txt
    
    # create config file
    python sunwind.py --config 
    
    # edit the file using whatever editor you fancy (gedit, vim, emacs, nano)
    nano ~/.sunwind.conf

    # test the script is working
    python sunwind.py
    
    # edit the cron config to point to the valid path
    nano cron_example
    
    # install the cron file
    crontab cron_example
        
# Usage
Try running `python sunwind.py -h` to see options. 
