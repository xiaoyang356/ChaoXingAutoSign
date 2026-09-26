import requests
from lxml import etree
import time
import os
import json
import sys
from login import Login

global currClass
currClass = 0
session = requests.session()


def login(username, password):
    global session
    session = requests.session()
    cookie_file = os.path.dirname(os.path.realpath(__file__)) + "/cookies.json"

    if os.path.exists(cookie_file):
        with open(cookie_file, "r") as f:
            try:
                session.cookies.update(json.loads(f.read()))
                print("cookies存在，使用cookies")
                return
            except Exception:
                pass

    url = 'http://passport2.chaoxing.com/fanyalogin'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0',
        'Referer': r'http://passport2.chaoxing.com/login?fid=&newversion=true&refer=http%3A%2F%2Fi.chaoxing.com'
    }
    my_login = Login(username, password)
    my_login.get_information()
    data = {
        'fid': -1,
        'uname': my_login.username,
        'password': my_login.password,
        'refer': r'http%253A%252F%252Fi.chaoxing.com',
        't': True,
        'forbidotherlogin': 0
    }

    res = session.post(url, headers=headers, data=data)
    with open(cookie_file, "w") as f:
        f.write(json.dumps(res.cookies.get_dict()))


def getclass():
    global course_dict
    course_dict = {}

    url = 'http://mooc1-2.chaoxing.com/visit/courses'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0',
        'Referer': r'http://i.chaoxing.com/'
    }
    res = session.get(url, headers=headers)

    if res.status_code == 200:
        class_HTML = etree.HTML(res.text)
        i = 0
        for class_item in class_HTML.xpath("/html/body/div/div[2]/div[3]/ul/li[@class='courseItem curFile']"):
            try:
                class_item_name = class_item.xpath("./div[2]/h3/a/@title")[0]
                i += 1
                course_dict[i] = [class_item_name,
                                  "https://mooc1-2.chaoxing.com{}".format(class_item.xpath("./div[1]/a[1]/@href")[0])]
            except Exception as e:
                print(e)
    else:
        print("error:课程处理失败")


def qiandao(url: str, address: str, sleepTime: int, SENDKEY: str):
    url_detail = 'https://mobilelearn.chaoxing.com/widget/pcpick/stu/index?courseId={courseid}&jclassId={clazzid}'.format(
        courseid=re.findall(r"courseid=(.*?)&", url)[0], clazzid=re.findall(r"clazzid=(.*?)&", url)[0])
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0',
    }
    res = session.get(url_detail, headers=headers)
    tree = etree.HTML(res.text)
    activeDetail = tree.xpath('/html/body/div[2]/div[2]/div/div/div/@onclick')
    if not activeDetail:
        print(course_dict[currClass][0] + "------暂无签到活动")
    else:
        print('\n')
        print(course_dict[currClass][0] + "------检测到：" + str(len(activeDetail)) + "个活动。")
        time.sleep(sleepTime)

        for activeID in activeDetail:
            global id
            id = re.findall(r'activeDetail\((.*?),', activeID)[0]
            enc = ''
            data = session.get(
                'https://mobilelearn.chaoxing.com/v2/apis/sign/refreshQRCode?activeId={id}'.format(id=id)).json()['data']
            if data is not None:
                enc = data['enc']

            url_sign = 'https://mobilelearn.chaoxing.com/pptSign/stuSignajax?activeId={id}&clientip=&latitude=-1&longitude=-1&appType=15&fid=0&enc={enc}&address={address}'.format(
                id=id, enc=enc, address=address)
            res = session.get(url_sign, headers=headers)
            print('**********')
            print(res.text)
            if '非签到活动' in res.text:
                continue
            push(SENDKEY, res)
        print('\n')


def push(SENDKEY, res):
    if SENDKEY == '':
        print("SENDKEY 为空，跳过推送")
        return

    if res.text == 'success':
        r = requests.post('https://sctapi.ftqq.com/{sendkey}.send'.format(sendkey=SENDKEY),
                          data={'text': "学习通-签到成功", 'desp': course_dict[currClass][0] + "签到成功"})
    elif res.text == '您已签到过了':
        r = requests.post('https://sctapi.ftqq.com/{sendkey}.send'.format(sendkey=SENDKEY),
                          data={'text': "学习通-已签到过了", 'desp': course_dict[currClass][0] + "您已签到过了"})
    else:
        r = requests.post('https://sctapi.ftqq.com/{sendkey}.send'.format(sendkey=SENDKEY),
                          data={'text': "学习通-签到失败", 'desp': "签到失败，原因：" + res.text})

    if r.status_code == 200:
        print("Server酱推送成功")
    else:
        print("Server酱推送失败")


if __name__ == '__main__':
    username = os.environ["USERNAME"]
    password = os.environ["PASSWORD"]
    SENDKEY = os.environ["SENDKEY"]
    address = os.environ["ADDRESS"]
    sleepTime = 10
    course_dict = {}

    # 核心修改：最多重试3次，防止死循环
    max_retries = 3
    retry_count = 0
    while course_dict == {} and retry_count < max_retries:
        login(username, password)
        getclass()
        if course_dict == {}:
            print("cookie过期或获取课程失败，重新登录 (第 {}/{} 次)".format(retry_count + 1, max_retries))
            cookie_file = os.path.dirname(os.path.realpath(__file__)) + "/cookies.json"
            if os.path.exists(cookie_file):
                os.remove(cookie_file)
            retry_count += 1
            time.sleep(2)

    if course_dict == {}:
        print("连续 {} 次获取课程失败，Cookie 已失效，任务强制退出。".format(max_retries))
        sys.exit(1)

    for currClass in course_dict:
        qiandao(course_dict[currClass][1], address, sleepTime, SENDKEY)
