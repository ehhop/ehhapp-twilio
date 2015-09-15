# todo for phone system

1. Add billing phone number option (call ACT chairs) - Lizzie
..*will patch in once I understand full call routing options

2. Fix blank voicemails getting sent - Lizzie 
..*fixed as of Twilio migration

3. Add extensions for phone numbers in clinic  - e.g. ACT CMs and Chronic Care Seniors - Joe-Ann
..*DONE

4. Integrate CareMessage in somehow (does CareMessage have a unique short code? cause that would make it easier)

5. Make HIPAA-compliant
..* turn off request inspector Twilio
..* http auth for media urls
..* download and delete call recordings - currently downloading but need to delete off Twilio server
..* speak with HIPAA staff

6. Port over phone number to Twilio
