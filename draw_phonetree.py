from ehhapp_twilio.config import *
import requests
import xml.etree.ElementTree as et
from graphviz import Digraph

select_digits = ['*','1','2','3','4','5','6','7','8','9']
dot = Digraph(comment='EHHAPP-twilio phone tree')
base_url = "https://twilio.ehhapp.org/"
params = "?From=+19739608144&AccountSid=" + twilio_AccountSID

def parse_url(curr_url, digits, params=params):
	response = requests.post(curr_url + params + "&Digits=" + str(digits))
	x = et.fromstring(response.text)
	for dial in x.findall('Dial'):
		return dial.text, None, "Dial", dial.text
	for gather in x.findall('Gather'):
		return gather.get('action'), gather.get('numDigits'), "Menu", spliturl(response.url)
	for record in x.findall('Record'):
		return record.get('action'), None, "Record", spliturl(response.url)
	return None, None, None, None

def main():
	last_url = "/" + spliturl(base_url)
	print last_url
	dot.node(last_url, "Home: " + base_url)
	next_url, digits, action, redirurl = parse_url(base_url, 0)
	dot.node(next_url, "Menu: " + next_url)
        dot.edge(last_url, next_url, label="ALL")
	# parse recursively
	for i in select_digits:
		get_response(last_url, next_url, i)
	dot.render('test-ehhapp.gv')

def get_response(last_url, curr_url, next_digit):
	next_url, digits, action, redir_url = parse_url(base_url + curr_url, next_digit)
	print curr_url, next_url, str(next_digit)
	if digits != None and (int(digits) > 1):
		dot.node(next_url, action + ": " + next_url)
       	        dot.edge(curr_url, next_url, label=next_digit)
		return None
	if (digits != '1') or (next_url == curr_url):
		if action != None:
			dot.node(redir_url, action + ": " + redir_url)
			dot.edge(curr_url, redir_url, label=next_digit)
			return None
	else:
                dot.node(next_url, action + ": " + next_url)
	        dot.edge(curr_url, next_url, label=next_digit)
                print next_url
		for i in select_digits:
			get_response(redir_url, next_url, i)
		return None
                


def spliturl(urlstring):
	return urlstring.split("/",3)[3].split("?")[0]

if __name__=='__main__':
	main()
		
