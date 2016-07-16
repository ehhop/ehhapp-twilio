.. title:: Intro

Intro
=====

Welcome. So you want to contribute to ehhapp-twilio? This is the high-level
technical overview you'll need before you start mucking around.

Basics
------

*Skip this if you are familiar with the concept of programming, HTTP, and the internet.*

The text in files in this folder contain all the instructions and messages 
necessary for a computer somewhere to handle phone calls, present options 
to callers, and route voicemails/redirect phone calls as necessary.

Pretty neat.

Because all of these instructions are implemented on "web servers" 
communicating over the internet, some principles and terminology will help.

Principles
^^^^^^^^^^

#. Computers do what they are told to do.
#. We tell computers what to do.
#. We use structured plain text to tell computers what to do.
#. Most of the time, a computer does one thing - a lot of times.

Terminology
^^^^^^^^^^^

* **Server** - a computer that is well-suited to communicating with other 
  computers, providing a "service" even. We tell servers what to do.
* **Language/Protocol** - the syntax and grammar of structured plain text 
  that we must follow in writing instructions so that they can be 
  understood by a computer, e.g. Python, Ruby, JavaScript.
* **Application/Software** - a collection of instructions for computers we use 
  again and again to solve higher level problems, e.g. Chrome, a browser 
  is just a set of instructions to a computer telling it to give us a 
  tool that accepts web address inputs and displays websites as output.
* **Hypertext Transfer Protocol** - the set of rules governing how messages 
  can and should be passed between applications distributed across 
  many servers all around the world, i.e. the internet.
* **Internet** - lots of computers running applications talking to each other 
  using HTTP, among other things.
* **Web application** - an application that is built to send stuff over the 
  internet using HTTP.
* **Web app framework** - a toolkit that makes it much easier to write 
  a functioning web application, e.g. Flask, Django, Sinatra, Rails, 
  Express.
* **Browser** - an application that sends, receives, and displays the content
  of HTTP messages.
* **HTML/CSS/JavaScript** - collection of languages that a browser understands 
  for displaying/rendering content and functionality. It makes up the 
  content of many HTTP messages.

Architecture
------------

ehhapp-twilio is meant to be deployed as a web application that responds 
to Twilio requests. Twilio requests are triggered by phone calls to a 
Twilio phone number.

The app is coded in Python using the popular Flask framework. Why Python? 
No particular reason. It is convenient. It is easy to learn. Why Flask? 
Flask is a legitimate production-quality web framework used by some 
big players: Pinterest, Twilio, LinkedIn to name a few.

Responses to Twilio requests are in TwiML, proprietary XML that tells 
Twilio what to do (e.g. present a menu of options, take voicemail, send 
keypad input, etc.). `See Twilio Docs`_

.. _See Twilio Docs: https://www.twilio.com/docs/api/twiml/twilio_request

*If your eyes are glazing over right now, you need an intro to the fundamentals of web programming (see above).*

Using TwiML we can get Twilio to record voicemails and securely send the audio 
to a data store with strict access control. This is the technical part of 
HIPAA compliance. For us, this safe place is Box.

To make it possible for EHHOP volunteers to receive voicemail notifications 
and have the ability to listen to audio we need to a reference a Google Sheet 
with volunteer on-call schedules and contact info.

Finally, to authenticate would-be listeners to the audio, they must provide 
valid Google Account credentials according to OAuth 2.0 protocol.

