# -*- coding: utf-8 -*-

import requests, re, sys, os, datetime, codecs, stat
from bs4 import BeautifulSoup
from os.path import expanduser

config = None
latest_html = None

# The settings file
home = expanduser("~")
settings_file = home + '/.sunwind.conf'
data_file = home + '/.sunwind.dat'
error_file = home + '/.sundwind.latest_error.html'

example_config = """\
ssn = 12345678901
pin = 1234
studweb = studweb.uio.no
"""
example_mail_config = """
smtp_server = smtp.uio.no
smtp_username = ola.nordmann
smtp_password = p4ssw0rd
from_addr = ola.nordmann@ifi.uio.no
to_addr = ola@nordmann.no
"""

studweb_settings = {

    'studweb.ntnu.no': {
        'term_used_for_semester': 'Termin',
        'expand_link_text': 'Oversikt'
    },

    'studweb.uio.no': {
        'term_used_for_semester': 'Semester',
        'expand_link_text': 'Se opplysninger om deg'
    }
}


class Mailer:
    def __init__(self, config):
        needed = ['from_addr', 'to_addr', 'smtp_password', 'smtp_username']
        missing = set(needed).difference(config)

        if missing:
            print("\nMissing email config values!\n\t " + ",".join(missing))
            sys.exit(1)

        self.__dict__.update(config)

    def send(self, subject, text):
        import smtplib
        from email.mime.text import MIMEText

        msg = MIMEText(text, _charset='utf8')
        msg['Subject'] = subject
        msg['From'] = self.from_addr
        msg['To'] = self.to_addr

        s = smtplib.SMTP_SSL(self.smtp_server, timeout=10)
        s.login(self.smtp_username, self.smtp_password)
        s.sendmail(self.from_addr, self.to_addr, msg.as_string())
        s.quit()

    def __str__(self):
        return str(self.__dict__)

class SubjectResult:

    def __init__(self, code, name, grade, semester):
        """Expects all strings to be unicode
        This will be true if given input from BeautifulSoup, as
        as internal data structures are using unicode"
        """
        self.__code = code
        self.__name = name
        self.__grade = grade
        self.__semester = semester

        import hashlib

        self.__bytes = self.__str__().encode('utf8')
        self.__hash = hashlib.md5(self.__bytes).hexdigest()

    # for use in sets and as keys in dicts
    def __hash__(self):
        return int(self.__hash, 16)

    # as str
    def __str__(s):
        return u" ".join([s.__code, s.__name, s.__grade, s.__semester])

    # for comparison
    def __eq__(s, o):
        return s.__code == o.__code \
               and s.__grade == o.__grade \
               and s.__semester == o.__semester

    def asBytes(self):
        return self.__bytes

    def asUnicode(self):
        s = self.__str__()
        assert is_unicode_str(s)
        return s


class PageParser:

    def parse_page_with_expanded_link_section_for_logout_url(self, html_page):
        return find_bulleted_link(html_page, 'Logg ut')

    def parse_page_with_expanded_link_section_for_results_url(self, html):
        soup = BeautifulSoup(html)
        link = soup.find_all("a", title="Se dine resultater")
        check(link, "Could not find <a> tag with title \"Se dine resultater\"", soup.prettify())

        return link[0]['href']

    def parse_page_for_product_section(self, page_html):
        soup = BeautifulSoup(page_html)
        products = soup.find_all ("section", "products_container")[0]

        return products;

    def parse_login_page_for_path_to_form_handler(self, login_html):
        soup = BeautifulSoup(login_html)
        form = soup.select("form[name=fnrForm]")[0]

        return form['action']

    def parse_login_page_for_form_values(self, login_html):
        """Parses the login page for form input (also hidden with pre-set values)

        Returns a dictionary with <input:value>
        """

        soup = BeautifulSoup(login_html)
        inputs = soup.select("form[name=fnrForm] input")

        attributes = [i.attrs for i in inputs]
        form_values = {}

        for a in attributes:
            form_values[a.get('name')] = a.get('value')

        return form_values


    def parse_result_page_for_results(self, html):
        """Parses products page and returns a list of the products

        html - the html of the page containing the results
        """

        assert html != None
        assert is_unicode_str(html)

        soup = BeautifulSoup(html)

        # parse the results table
        products = soup.find_all("div", {"class": "product_item"})
        assert len(products) > 0

        for product in products:
            desc = product.find("div", "p_list_description")
            print desc.h4.text.strip()

        return products 


def is_unicode_str(s):
    if sys.version_info >= (3, 0, 0):
        # for Python 3
        return not isinstance(s, bytes)
    else:
        # for Python 2 
        return isinstance(s, unicode)


def open_page(session, parser):
    r = requests.get("https://www.sunwind.no/Outlet/")
    products_html = parser.parse_page_for_product_section(r.content);
    return products_html;


def check(find_result, error_msg, failing_html):
    if not find_result:
        f = codecs.open(error_file, 'w', encoding='utf8')
        decoded = codecs.decode(failing_html, 'iso8859-1')
        f.write(decoded)
        f.close()
        raise Exception(error_msg)


def diff(old, new):
    return new.difference(old)


def new_results(parser):
    return diff(old_results(parser), latest_results(parser))


def old_results(parser):
    if os.path.isfile(data_file):
        f = codecs.open(data_file, 'r', encoding='utf8')
        previous_html = f.read()
        f.close()
        return parser.parse_result_page_for_results(previous_html)
    return set()


def latest_results(parser):
    global latest_html

    session = requests.Session()  # The session object that persists cookies and default values across requests
    html = None

    products_html = open_page(session, parser)
    assert products_html
    html = products_html.prettify()
    latest_html = html

    return parser.parse_result_page_for_results(latest_html)


def find_bulleted_link(html, text_to_match):
    soup = BeautifulSoup(html)

    a = soup.find(lambda tag: tag.name == 'a' and tag.has_attr('href') and text_to_match in tag.text)

    check(a, 'Did not find "' + text_to_match + '".', html)

    return a['href']


def store(html):
    f = codecs.open(data_file, 'w', encoding='utf8', errors='ignore')
    f.write(html)
    f.close()


def get_parser():
    return PageParser()


def modification_date(filename):
    import os.path

    t = os.path.getmtime(filename)
    return datetime.datetime.fromtimestamp(t)


# Standardize printing of text for Python 2 and Python 3
def _print(s):
    assert is_unicode_str(s), "Not unicode: " + s
    if sys.version_info < (3, 0, 0):
        write = sys.stdout.write
    else:
        write = sys.stdout.buffer.write

    write((s + '\n').encode('utf-8'))


def print_error(s):
    sys.stderr.write((s + '\n').encode('utf-8'))
    sys.stderr.flush()


def read_config():
    config = None
    if os.path.isfile(settings_file):
        check_permissions()

        config = {}
        fp = open(settings_file, 'r')
        for l in fp.readlines():
            if len(l.strip()) == 0: continue

            k, v = [s.strip() for s in l.split("=")]
            config[k] = v
        fp.close()

    return config


def write_example_config(include_mail_config):
    fp = open(settings_file, 'w')
    fp.write(example_config)
    if include_mail_config:
        fp.write(example_mail_config)
    fp.close()

    # Make the file readable and writable by user only
    os.chmod(settings_file, stat.S_IRUSR | stat.S_IWUSR)

    print("Example config written to " + settings_file)
    print("Change values as necessary")


def send_mail(subject, body, config):
    mailer = Mailer(config)

    _print(u"\nMailing results to " + config['to_addr'])
    mailer.send(subject, body)
    _print(u"\nMail sent successfully")


def check_permissions():
    mode = os.stat(settings_file).st_mode

    if mode & stat.S_IROTH or mode & stat.S_IRGRP:
        print("The settings file should only be readable by the user!")
        print("Use `chmod 400 ~/.sunwind.conf` to make it private")
        sys.exit(1)


if __name__ == '__main__':

    import argparse

    argument_parser = argparse.ArgumentParser(description="Retreive sunwind results")
    argument_parser.add_argument("--mail",
                                 help="Use the built-in mailer instead of relying on cron to mail the results",
                                 action="store_true")
    argument_parser.add_argument("--quiet", help="Prevent output when there are no new results", action="store_true")
    argument_parser.add_argument("--config", help="Creates a default config file. Pass --mail to add email values",
                                 action="store_true")
    args = argument_parser.parse_args()

    body = ""
    subject = None
    config = read_config()

    if not config:

        if args.config:
            write_example_config(args.mail)
        else:
            print("No config file found. Try passing --help for more info")

        sys.exit(1)

    new = new_results(get_parser())

    if new:
        subject = u"Found new results since last check!"
        _print(subject)

        for result in new:
            result = result.asUnicode()
            body += u"\n - " + result

        _print(u"\nNew results:" + body)

        _print(u"\nStoring results ...")
        store(latest_html)

        if args.mail:
            send_mail(subject, body, config)

    elif not args.quiet:
        _print(u"No new results since " + str(modification_date(data_file)))

    sys.exit(0)
