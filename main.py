import os
import pytz
from time import sleep
import zmail
import sqlite3
import datetime
from pathlib import Path
from traceback import print_exc

BASE_DIR = Path(__file__).parent

help_url = 'https://jingyan.baidu.com/article/7908e85cd945fcaf481ad2e4.html'

print('正在连接数据库...')
db = sqlite3.connect(BASE_DIR / "data.sqlite3")
db.execute("CREATE TABLE IF NOT EXISTS email_account(id INT PRIMARY KEY NOT NULL, email TEXT,code TEXT);")
db.execute("CREATE TABLE IF NOT EXISTS email_info(id INTEGER PRIMARY KEY AUTOINCREMENT, email_id INT, account TEXT);")
print('数据库已就绪!')

if __name__ == '__main__':
    while 1:
        T = input('请输入一个不大于3000的正整数，作为每一次查收邮件的间隔时间，单位为秒：')
        if T.isdigit():
            T = int(T)
            if 0 < T <= 3000:
                break
        print('您的输入不正确')

    # 连接邮箱服务器
    while 1:
        email_accounts = db.execute("SELECT * FROM email_account").fetchall()
        if email_accounts:
            email_account = email_accounts[0]
            server = zmail.server(email_account[1], email_account[2])
            if server.smtp_able() and server.pop_able():
                print('服务器连接成功！')
                break

            print('服务器连接失败，原因：网络故障或邮箱地址与识别码不匹配')
            if not input("是否重新输入账号信息：yes或no？：") in ['yes', 'ye', 'y', 'Y', 'Ye', 'Yes', 'YES']:
                input('请敲击回车来终止程序')
                raise KeyboardInterrupt
        print(f'请确保您输入的邮箱开启了pop3/smtp服务，并获取对应的邮箱识别码（并不是邮箱密码），如果您不清楚如何开启，可以参考该网页：{help_url}')
        email = input('请输入您的邮箱：')
        code = input('请输入对应的邮箱识别码：')
        if db.execute("SELECT * FROM email_account WHERE id=1").fetchall():
            sql = f'UPDATE email_account SET email="{email}", code="{code}" WHERE id=1;'
        else:
            sql = f'INSERT INTO email_account VALUES (1, "{email}", "{code}");'
        db.execute(sql)
        db.commit()

    while 1:
        try:
            threshold_time = (datetime.datetime.now() - datetime.timedelta(hours=1)).replace(
                tzinfo=pytz.timezone('Asia/Shanghai'))
            print('\n\n正在获取邮件信息，这个过程可能需要几分钟，请稍后...')
            before = datetime.datetime.now()
            mails = server.get_mails(start_time=threshold_time)
            print(f'邮件获取成功！用时：{(datetime.datetime.now() - before).seconds}秒')

            num = 0
            for mail in mails:
                from_ = mail['from']
                account = email_account[1]
                email_id = mail['Id']
                sql1 = f'SELECT * FROM email_info WHERE email_id={email_id} and account="{account}"'
                if db.execute(sql1).fetchall():
                    continue
                else:
                    num += 1
                    sql2 = f'INSERT INTO email_info (email_id,account) VALUES ({email_id},"{account}")'
                    db.execute(sql2)
                    db.commit()

                # zmail.show(mail)
                if mail['Attachments']:
                    output_path = BASE_DIR / email_account[1]
                    if not os.path.exists(output_path):
                        os.mkdir(output_path)
                    zmail.save_attachment(mail, target_path=output_path.__str__(), overwrite=True)
                    print(f'收到了来自{from_}的邮件，主题为{mail["Subject"]}，其附件已保存到本地')
                else:
                    print(f'收到了来自{from_}的邮件，主题为{mail["Subject"]}，无附件')
            print(f'{datetime.datetime.now().strftime("%H:%M:%S")}:  本次查收了{num}封邮件')

            for step in range(T):
                print(f'\r{datetime.datetime.now().strftime("%H:%M:%S")}:  距离下一次查收邮件还有 {T - step}秒', end='')
                sleep(1)
        except KeyboardInterrupt:
            break
        except:
            print_exc()
