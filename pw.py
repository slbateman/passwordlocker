#! user/bin/Python
# pw.py Password Locker program

import getpass
import os, random, struct
import pyperclip
import sqlite3
from Crypto.Cipher import AES
import hashlib

password = ""
db = "pwlocker.db"

def create_password(password):
    print "This is your first time."
    while password == "":
        password_fst = getpass.getpass(prompt="Create Locker Password > ")
        password_sec = getpass.getpass(prompt="Confirm Locker Password > ")
        if password_fst == password_sec:
            password = password_fst
        else:
            print "Passwords don't match"
    return password


def get_password(password):
    password = getpass.getpass(prompt="Enter LockerPassword")
    return password


if os.path.exists(db+".enc") == True:
    password = get_password(password)
else:
    password = create_password(password)
key = hashlib.sha256(password).digest()


def encrypt_file(key, db, out_filename=None, chunksize=64*1024):
    """ Encrypts a file using AES (CBC mode) with the
        given key.

        key:
            The encryption key - a string that must be
            either 16, 24 or 32 bytes long. Longer keys
            are more secure.

        db:
            Name of the input file

        out_filename:
            If None, '<db>.enc' will be used.

        chunksize:
            Sets the size of the chunk which the function
            uses to read and encrypt the file. Larger chunk
            sizes can be faster for some files and machines.
            chunksize must be divisible by 16.
    """
    if not out_filename:
        out_filename = db + '.enc'

    iv = ''.join(chr(random.randint(0, 0xFF)) for i in range(16))
    encryptor = AES.new(key, AES.MODE_CBC, iv)
    filesize = os.path.getsize(db)

    with open(db, 'rb') as infile:
        with open(out_filename, 'wb') as outfile:
            outfile.write(struct.pack('<Q', filesize))
            outfile.write(iv)

            while True:
                chunk = infile.read(chunksize)
                if len(chunk) == 0:
                    break
                elif len(chunk) % 16 != 0:
                    chunk += ' ' * (16 - len(chunk) % 16)

                outfile.write(encryptor.encrypt(chunk))
                os.remove(db)


def decrypt_file(key, db, out_filename=None, chunksize=24*1024):
    """ Decrypts a file using AES (CBC mode) with the
        given key. Parameters are similar to encrypt_file,
        with one difference: out_filename, if not supplied
        will be db without its last extension
        (i.e. if db is 'aaa.zip.enc' then
        out_filename will be 'aaa.zip')
    """
    if not out_filename:
        out_filename = os.path.splitext(db)[0]

    with open(db, 'rb') as infile:
        origsize = struct.unpack('<Q', infile.read(struct.calcsize('Q')))[0]
        iv = infile.read(16)
        decryptor = AES.new(key, AES.MODE_CBC, iv)

        with open(out_filename, 'wb') as outfile:
            while True:
                chunk = infile.read(chunksize)
                if len(chunk) == 0:
                    break
                outfile.write(decryptor.decrypt(chunk))

            outfile.truncate(origsize)
            os.remove(db)


try:
    decrypt_file(key, db=db+".enc")
except IOError:
    pass


conn = sqlite3.connect(db)
c = conn.cursor()
conn.text_factory = str


c.execute("""CREATE TABLE IF NOT EXISTS pwds(
    pwdID INTEGER PRIMARY KEY, site TEXT, usrnm TEXT, pwd TEXT)""")
conn.commit()


def getSite():
    site = ""
    site = raw_input("Enter Web Address > ")
    return site


def checkSite(site):
    c.execute("""SELECT * FROM pwds WHERE site = ? LIMIT 1""", (site,))
    exists = c.fetchall()
    return exists


def getUsrnm():
    usrnm = raw_input("Enter User Name > ")
    return usrnm


def getPwd():
    print "<< Password Must exceed 12 Characters"
    print "<< lowercase, uppercase, numbers, special characters"
    pwd = getpass.getpass(prompt="Enter Password > ")
    if len(pwd) >= 12:
        pwd2 = getpass.getpass(prompt="Confirm Password > ")
        if pwd == pwd2:
            pass
        else:
            print "<<<< Passwords do not match >>>>"
            pwd = ""
    else:
        print "<<<< Password is not long enough >>>>"
        pwd = ""
    return pwd


class CopyPwd(object):
    def enter(self):
        site = ""
        pwd = ""
        while site == "":
            site = getSite()
            exists = checkSite(site)
            if exists:
                break
            else:
                print "Site not found"
        c.execute("""SELECT pwd FROM pwds WHERE site = ?""", (site,))
        pwd = c.fetchone()[0]
        pyperclip.copy(pwd)
        print "The password for '%s' has been copied to your clipboard" % site


class ChangePwd(object):
    def enter(self):
        site = ""
        pwd = ""
        while site == "":
            site = getSite()
            exists = checkSite(site)
            if exists:
                break
            else:
                print "Site not found"
        print "<< Set New Password"
        while pwd == "":
            pwd = getPwd()
        c.execute("""UPDATE pwds SET pwd = ? WHERE site = ? """, (pwd, site))
        print "Your new password for '%s' has been saved" % site
        conn.commit()


class NewPwd(object):
    def enter(self):
        site = ""
        usrnm = ""
        pwd = ""
        while site == "":
            site = getSite()
            exists = checkSite(site)
            if exists:
                site = ""
                print "That site already has an entry"
            else:
                break
        usrnm = getUsrnm()
        while pwd == "":
            pwd = getPwd()
        c.execute("""INSERT INTO pwds(site, usrnm, pwd) VALUES(?,?,?)""",
                 (site, usrnm, pwd))
        conn.commit()
        print "<<<Your password and username have been saved for '%s'" % site


class List(object):
    def enter(self):
        c.execute("""SELECT site, usrnm FROM pwds ORDER BY site""")
        viewList = c.fetchall()
        for x in viewList:
            print "SITE: %s\nUSERNAME: %s\n" % (x[0], x[1])


class DeletePwd(object):
    def enter(self):
        print "Which account would you like to delete?"
        site = ""
        pwd = ""
        while site == "":
            site = getSite()
            exists = checkSite(site)
            if exists:
                break
            else:
                print "Site not found"
        c.execute("""DELETE FROM pwds WHERE site=?""", (site,))
        conn.commit()
        print "<<<< All data for '%s' has been deleted >>>>" % site
        


class Quit(object):
    def enter(self):
        conn.commit()
        c.close()
        conn.close()
        encrypt_file(key, db)
        quit()


class Cmds(object):
    cmds = {
        'NEW': NewPwd(),
        'CHANGE': ChangePwd(),
        'COPY': CopyPwd(),
        'LIST': List(),
        'DELETE': DeletePwd(),
        'QUIT': Quit()
    }

    def enter(self):
        while 1 == 1:
            cmd = raw_input("""\n<<<<Enter:>>>>
    'NEW' to save a new password
    'CHANGE' to change a saved password
    'COPY' to select a password to copy to your clipboard
    'LIST' to view a list of all accounts with saved passwords
    'DELETE' to delete saved password for a selected site
    'QUIT' to exit program
> """).upper()
            if cmd in self.cmds.keys():
                command = self.cmds.get(cmd)
                command.enter()
            else:
                print "Invalid Input"


command = Cmds()
command.enter()



