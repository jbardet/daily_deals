from config import EMAIL_SENDER, EMAIL_RECIPIENTS, EMAIL_PASSWORD


def send_email(subject, body, sender, recipients, password):
    # # body['Subject'] = subject
    # # body['From'] = sender
    # # body['To'] = ', '.join(recipients)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
    # with smtplib.SMTP('smtp.gmail.com', 465, timeout=60) as smtp_server:
        # smtp_server.starttls(context=ssl.create_default_context())
        smtp_server.login(sender, password)
        smtp_server.sendmail(sender, recipients, body.as_string())
        # smtp_server.send_message(body)
    # # smtp = smtplib.SMTP()
    # # smtp.connect('smtp.gmail.com')
    # # smtp.login(sender, password)
    # # smtp.sendmail(sender, sender, body.as_string())
    # # smtp.quit()
    # s = smtplib.SMTP('smtp.gmail.com', 465) # 587)
    # s.ehlo()
    # s.login(sender, password)
    # s.sendmail(msgRoot['From'], recipients[0], msgRoot.as_string())
    # s.quit()
    print("Message sent!")

def main():
    # load json file with data
    path = Path(__file__).with_name("todays_ids.json")
    with open(path) as json_file:
        data = json.load(json_file)

    msgRoot = EmailMessage()
    sender = EMAIL_SENDER
    recipients = EMAIL_RECIPIENTS
    password = EMAIL_PASSWORD

    # msgRoot = MIMEMultipart('alternative') # related
    msgRoot['From'] = sender
    msgRoot['Subject'] = "Deals"
    msgRoot['To'] = recipients
    # msgRoot.preamble = 'This is a multi-part message in MIME format.'

    msgRoot = create_htm_from_deals(data, msgRoot)

    # save to disk a local copy of the message
    Path('outgoing.msg').write_bytes(bytes(msgRoot))

    # alternative = MIMEMultipart("related")
    # msgRoot.attach(alternative)
    # text_content= "YOOOO"
    # msgRoot.attach(MIMEText(text_content))

    # # We reference the image in the IMG SRC attribute by the ID we give it below
    # msgText = MIMEText('<b>Some <i>HTML</i> text</b> and an image.<br><img src="cid:image1"><br>Nifty!', 'html')
    # msgRoot.attach(msgText)

    # # # define your location
    # # URL = 'https://static.digitecgalaxus.ch/productimages/4/4/8/5/6/8/9/0/0/3/4/3/1/9/6/9/1/6/0/55701669-03da-4b64-b382-d27fe1aa485d_cropped.jpg'
    # # with urllib.request.urlopen(URL) as url:
    # #     with open('temp.jpg', 'wb') as f:
    # #         f.write(url.read())

    # img = open('temp.jpg', 'rb')
    # # Attach your image
    # msg_img = MIMEImage(img.read())
    # img.close()

    # # Define the image's ID as referenced above
    # msgRoot.add_header('Content-ID', '<image1>')
    # msgRoot.attach(msg_img)

    send_email("", msgRoot, sender, recipients, password)

if __name__ == "__main__":
    main()
