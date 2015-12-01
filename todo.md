# todo for phone system

1. Add billing phone number option (call ACT chairs) - Lizzie
..* will patch in once I get around to it
2. Fix blank voicemails getting sent - Lizzie 
..* fixed as of Twilio migration
3. Add extensions for phone numbers in clinic  - e.g. ACT CMs and Chronic Care Seniors - Joe-Ann
..* DONE
4. Integrate CareMessage in somehow (does CareMessage have a unique short code? cause that would make it easier)
5. Make HIPAA-compliant
..* turn off request inspector Twilio - DONE
..* http auth for media urls - DONE
..* download and delete call recordings - DONE
..* validate setup with HIPAA staff - ???
..* move over to box on MSSM - DONE
..* https - need to talk with ASCIT
6. Port over phone number to Twilio

# kevin silly questions

1. Should we use suds instead of SOAPpy?
2. Why do we use FTP instead of FTP_TLS for playing voicemails?
