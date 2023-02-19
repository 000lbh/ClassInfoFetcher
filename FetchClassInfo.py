import getpass
import json
import os
import sys
import re
import time
import random
import ctypes
import base64
from urllib import request,parse
from http.cookiejar import CookieJar

header=('User-Agent','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36 Edg/98.0.1108.55')
AlwaysRefresh=False
AutoRecog = True
NULL = 0
DoubleMajor = ''

if AutoRecog:
    import ddddocr

class CustomizedException:
    class LoginError(Exception):
        def __init__(self,text):
            self.text=text
    class SessionExpired(Exception):
        def __init__(self,text):
            self.text=text
    class Refresh(Exception):
        def __init__(self, text):
            self.text = text

def recog_auto(pic):
    ocr = ddddocr.DdddOcr()
    return '1000', ocr.classification(pic)

def recog_manual(pic):
    fn = str(random.random()) + '.jpg'
    f = open(fn, mode='wb')
    f.write(pic)
    f.close()
    print('Open', fn, 'and input captcha here:')
    return 'No ID',input()

def fdbk_auto(id):
    return 'No feedback'

def fdbk_manual(id):
    return '1231234567'

recog = recog_auto if AutoRecog else recog_manual
fdbk = fdbk_auto if AutoRecog else fdbk_manual

def IAAALogin(username,password,logfile,screenoutputfile):
    loginData=parse.urlencode([
        ('appid','syllabus'),
        ('userName',username),
        ('password',password),
        ('randCode',''),
        ('smsCode',''),
        ('otpCode',''),
        ('redirUrl','http://elective.pku.edu.cn:80/elective2008/ssoLogin.do')])
    screenoutputfile.write(time.asctime()+' IAAA登录中\n')
    req=request.Request('https://iaaa.pku.edu.cn/iaaa/oauthlogin.do')#IAAA登录
    req.add_header(*header)
    with request.urlopen(req,data=loginData.encode('utf-8')) as iaaa:
        pagedata=iaaa.read()
        logfile.write(time.asctime()+' IAAA Status: '+str(iaaa.status)+' '+iaaa.reason+'\n')
        for k,v in iaaa.getheaders():
            logfile.write('%s:%s'%(k,v)+'\n')
    logfile.write('-'*20+'\n')
    logonData=json.loads(pagedata.decode('utf-8'))
    try:
        token=logonData['token']
        return token
    except KeyError:
        screenoutputfile.write(time.asctime()+' Invalid Username or Password, or IAAA Died. Please Try Again.\n')
        logfile.write(time.asctime()+' Invalid Username or Password, or IAAA Died. Please Try Again.\n')
        logfile.write(repr(logonData)+'\n')
        raise CustomizedException.LoginError('Invalid Username or Password, or IAAA Died. Please Try Again')

def ElectiveLogin(username,token,logfile,screenoutputdata):
    global DoubleMajor
    try:
        screenoutputdata.write(time.asctime()+' **网登录中\n')
        cookie=CookieJar()#准备Cookies
        handler=request.HTTPCookieProcessor(cookie)
        opener=request.build_opener(handler)
        req=request.Request('http://elective.pku.edu.cn:80/elective2008/ssoLogin.do?_rand=%f&token=%s'%(random.random(),token))
        req.add_header(*header)
        elective = opener.open(req)
        pagedata=elective.read()
        pat = re.compile(r'http://elective\.pku\.edu\.cn:80/elective2008/scnStAthVef\.jsp/\.\./ssoLogin\.do\?.*?&sttp=') #No greedy match
        lat_pagedata = str(pagedata, encoding='latin')
        zfx = pat.findall(lat_pagedata)
        if zfx:
            while not DoubleMajor:
                DoubleMajor=input('Type fx for minor/double major, other for major')
            if DoubleMajor == 'fx':
                req = request.Request(zfx[1] + 'bfx')
                req.add_header(*header)
                elective = opener.open(req)
            else:
                req = request.Request(zfx[0] + 'bzx')
                req.add_header(*header)
                elective = opener.open(req)
            pagedata = elective.read()
        f=open('help.html',mode='wb')
        f.write(pagedata)
        f.close()
        logfile.write('Elective Login Status: '+str(elective.status)+' '+elective.reason+'\n')
        for k,v in elective.getheaders():
            logfile.write('%s:%s'%(k,v)+'\n')
        logfile.write('Cookies:\n')
        for i in cookie:
            logfile.write(i.name+'='+i.value+'\n')
        logfile.write('-'*20+'\n')
        for i in range(20):
            screenoutputdata.write(time.asctime()+' 下载验证码. . .\n')
            logfile.write(time.asctime()+' Downloading captcha. . .\n')
            req=request.Request('https://elective.pku.edu.cn/elective2008/DrawServlet?Rand='+str(random.random()*10000))
            referer = 'https://elective.pku.edu.cn/elective2008/edu/pku/stu/elective/controller/help/HelpController.jpf'
            req.add_header('referer',referer)
            req.add_header(*header)
            req.add_header(*('Connection','keep-alive'))
            with opener.open(req) as validpic:
                validpicstream=validpic.read()
                f=open('valid.pic',mode='wb')
                f.write(validpicstream)
                f.close()
            id, captcha = recog(validpicstream)
            log.write('ID: %s, Captcha code: %s\n' % (id, captcha))
            log.flush()
            req=request.Request('https://elective.pku.edu.cn/elective2008/edu/pku/stu/elective/controller/supplement/validate.do')
            req.add_header(*header)
            req.add_header('referer',referer)
            req.add_header(*('Connection','keep-alive'))
            validdata=parse.urlencode([
                ('xh',username),
                ('validCode',captcha)
            ])
            if int(json.loads(opener.open(req,data=validdata.encode('utf-8')).read().decode('utf-8'))['valid'])==2:
                screenoutputdata.write('验证成功，开始\n')
                logfile.write('Correct!\n')
                break
            else:
                screenoutputdata.write('验证失败，这是第%d次\n' % (i + 1))
                logfile.write('Wrong! This is the %dth(st, nd, rd) time.\n' % (i + 1))
        return opener
    except request.HTTPError:
        screenoutputdata.write(time.asctime()+' Elective site died!\n')
        logfile.write(time.asctime()+' Elective site died!\n')
        raise

def CourseAnalyze(opener,username,logfile,screenoutputfile):
    pat1=re.compile(r'<td class="datagrid"><a href="/elective2008/edu/pku/stu/elective/controller/supplement/goNested\.do\?course_seq_no=BZ.*" target="_blank" style="width: .*">')
    pat2=re.compile(r'<form name="pageForm" action="supplement\.jsp" style=".*">')
    pat3=re.compile(r'<a href="/elective2008/edu/pku/stu/elective/controller/supplement/supplement\.jsp\?netui_pagesize=electableListGrid%3B20&amp;netui_row=electableListGrid%3B.*?">.*?</a>')
    pat4=re.compile(r'<td class="datagrid".*?>.*?</td>')
    pat5=re.compile(r'<span>.*?</span>')
    pat6=re.compile(r'<td class="datagrid" align="center"><span id="electedNum.*?".*?>.*? </span></td>')
    pat7=re.compile(r'href="/elective2008/edu/pku/stu/elective/controller/supplement/electSupplement\.do\?.*?"')
    pat8=re.compile(r'index=.*?&')
    pat9=re.compile(r'seq=.*?&')
    lhelpcontroller='https://elective.pku.edu.cn/elective2008/edu/pku/stu/elective/controller/help/HelpController.jpf'
    lsupplycancel='https://elective.pku.edu.cn/elective2008/edu/pku/stu/elective/controller/supplement/SupplyCancel.do?xh='+str(username)
    req=request.Request(lsupplycancel)
    req.add_header('referer',lhelpcontroller)
    req.add_header(*header)
    req.add_header(*('Connection','keep-alive'))
    screenoutputfile.write(time.asctime()+' Getting course table. . .\n')
    logfile.write(time.asctime()+' Getting course table. . .\n')
    try:
        with opener.open(req) as eSupplyCancel:
            logfile.write(time.asctime()+' Supply Cancel Status: '+str(eSupplyCancel.status)+' '+eSupplyCancel.reason+'\n')
            for k,v in eSupplyCancel.getheaders():
                logfile.write('%s:%s'%(k,v)+'\n')
            pagedata=eSupplyCancel.read()
            supcan=open('supcan.html',mode='wb')
            supcan.write(pagedata)
            supcan.close()
            assert b'11-1.png' not in pagedata
        screenoutputfile.write(time.asctime()+' Analyzing course data. . .\n')
        rawCourseTable=pat1.split(pat2.split(bytes.decode(pagedata,encoding='utf-8',errors='replace'))[0])[1:]
        CourseTable=[]
        for i in rawCourseTable:
            data=pat4.findall(i)
            course=[pat5.findall(i)[0][6:-7]]
            course.append(data[4].split('>')[-3][:-6])
            course.append(pat6.findall(i)[0].split('>')[-3][:-7].split(' / ')[0])#limitNum
            course.append(pat7.findall(i)[0][7:-1].replace('&amp;','&'))#electLink
            course.append(pat8.findall(course[-1])[0][6:-1])#index
            course.append(pat9.findall(course[-2])[0][4:-1])#seq
            course.append(data[3].split('>')[2][:-6])#teacher
            CourseTable.append(tuple(course))
        return CourseTable, '/ ' in pat6.findall(i)[0].split('>')[-3][:-7].split(' / ')[1]
    except AssertionError:
        logfile.write(time.asctime()+' Session expired.Relogging in. . .\n')
        screenoutputfile.write(time.asctime()+' Session expired.Relogging in. . .\n')
        raise CustomizedException.SessionExpired('Session expired.')

def SelectCourseIndex(CourseTable, ClassNo, IntnlCourseNo):
    for i, j in enumerate(CourseTable):
        if j[1] == ClassNo and j[5] == IntnlCourseNo:
            return i
    return None

def SpiderLoop(opener,username,coursetable,choosetable,logfile,screenoutputfile,waiting=False):
    referer='http://elective.pku.edu.cn:80/elective2008/ssoLogin.do?token='+token
    for i in choosetable:
        limitNum=int(coursetable[i][2])
        index=coursetable[i][4]
        seq=coursetable[i][5]
        electlink=coursetable[i][3]
        req=request.Request('https://elective.pku.edu.cn/elective2008/edu/pku/stu/elective/controller/supplement/refreshLimit.do')
        req.add_header('referer',referer)
        req.add_header(*header)
        req.add_header(*('Connection','keep-alive'))
        enquiredata=parse.urlencode([
            ('index',index),
            ('seq',seq),
            ('xh',username)
        ])
        with opener.open(req,data=enquiredata.encode('utf-8')) as eEnquire:
            try:
                if not waiting:
                    numDict = json.loads(eEnquire.read().decode('utf-8'))
                    electedNum=int(numDict['electedNum'])
                    limitNum=int(numDict['limitNum'])
            except ValueError:
                raise CustomizedException.SessionExpired('Session Expired.')
        if waiting or limitNum > electedNum:
                screenoutputfile.write(time.asctime()+' '+coursetable[i][0]+'目前可！尝试中\n')
                logfile.write(time.asctime()+' Name:'+coursetable[i][0]+'Class NO.:'+coursetable[i][1]+' is available now!\n')
                assert 'cancelCourse.do' not in electlink # No-cancel ensurance
                req=request.Request('https://elective.pku.edu.cn/'+electlink)
                req.add_header('referer',referer)
                req.add_header(*header)
                req.add_header(*('Connection','keep-alive'))
                f=open('result.html',mode='wb')
                resultpage=opener.open(req).read()
                f.write(resultpage)
                f.close()
                if b'/elective2008/resources/images/success.gif' in resultpage:
                    print('可能成功')
                    logfile.write(time.asctime()+' Election may success, check result.html!\n')
                    if os.name == 'nt':
                        ctypes.windll.user32.MessageBeep(0x40)
                        ctypes.windll.user32.MessageBoxW(NULL, '请查看result.html确定是否成功，程序暂停', '提示', 65)
                        if ctypes.windll.user32.MessageBoxW(NULL, '是否继续？', '询问', 36) == 7: #Magic number 7 means NO, 6 means YES
                            raise KeyboardInterrupt
                    else:
                        input('请查看result.html确定是否成功，程序暂停，按回车键继续，按ctrl+c终止')
                    break
                else:
                    print('失败')
                    logfile.write(time.asctime()+' Election failed.\n')
                    raise CustomizedException.SessionExpired('Election failed!')
        else:
            screenoutputfile.write(time.asctime()+' '+coursetable[i][0]+'目前不可\n')
            logfile.write(time.asctime()+' Name:'+coursetable[i][0]+'Class NO.:'+coursetable[i][1]+' is not available.\n')
            logfile.flush()
        time.sleep(5+random.random()*3)

print('****************')
print('按下Ctrl + C停止')
try:
    log=open('log'+str(time.time())+'.log',mode='w')
    choosetable=[]
    montable=[]
    loggedin=False
    while 1:
        try:
            while 1:
                try:
                    if not loggedin:
                        username=input('用户名（学号）：')
                        password=getpass.getpass(prompt='密码（不显示）：')
                    token=IAAALogin(username,password,log,sys.stdout)
                    if os.name == 'nt':
                        ctypes.windll.user32.MessageBeep(0x10)
                    print('<-New Block->')
                    loggedin=True
                    break
                except CustomizedException.LoginError:
                    pass
            for i in range(5):
                try:
                    opener=ElectiveLogin(username,token,log,sys.stdout)
                    log.flush()
                    break
                except request.HTTPError:
                    log.write(time.asctime()+' Login elective failed,retry.This is the '+str(i+1)+'th(st,nd,rd) attempt.')
                    print(time.asctime(),'Login elective failed, retry.')
            else:
                print(time.timeasc(),'Maximum attempts reached but still failed to login elective.')
                log.write(time.asctime()+' Maximum attempts reached but still failed to login elective.')
                raise CustomizedException.LoginError('Elective login failed.')
            try:
                coursetable,isWaiting=CourseAnalyze(opener,username,log,sys.stdout)
            except request.HTTPError:
                raise
            except CustomizedException.SessionExpired:
                continue
            for i,j in enumerate(coursetable):
                print('序号：%d\n课程名：%s\n班号:%s\n限数:%s\n内部课程号：%s\n老师：%s\n'%(i,*j[0:3],j[5],j[6]))
                log.write('No:%d\nCourseName:%s\nClassNo:%s\nLimit:%s\nInternalCourseNo:%s\nTeacher(s):%s\nElectLink:%s\n\n'%(i,*j[0:3],j[5],j[6],j[3]))
                log.flush()
            if not montable:
                while 1: # Give an empty input to break the loop
                    cn = input('班号（不是序号！）')
                    icn = input('内部课号')
                    t = SelectCourseIndex(coursetable, cn, icn)
                    if t == None:
                        break
                    montable.append((cn, icn))
                    choosetable.append(t)
            else:
                for cn, icn in montable:
                    t = SelectCourseIndex(coursetable, cn, icn)
                    if t != None:
                        choosetable.append(t)
            log.write('You have chosen to monitor class %s\n'%' '.join(map(str,choosetable)))
            try:
                while 1:
                    try:
                        SpiderLoop(opener,username,coursetable,choosetable,log,sys.stdout,isWaiting)
                        if AlwaysRefresh:
                            log.write(time.asctime()+'Refreshing as user required. . .\n')
                            raise CustomizedException.Refresh('User required')
                    except CustomizedException.Refresh:
                        coursetable, isWaiting = CourseAnalyze(opener, username, log, sys.stdout)
                    log.flush()
            except CustomizedException.SessionExpired:
                print(time.asctime()+' Session expired.Relogging in. . .')
                log.write(time.asctime()+' Session expired.Relogging in. . .\n')
            except AssertionError:
                print(time.asctime()+' Cancel protection activated! Check the log file!')
                log.write(time.asctime()+' Cancel protection activated!\n')
        except KeyboardInterrupt:
            raise
        except SystemExit:
            raise
        except request.HTTPError as e:
            print(time.asctime()+' Network error,try again. . .')
            log.write(time.asctime()+' Network error,try again. . .\n')
        except Exception as e:
            print(time.asctime()+' An uncaught exception occurred!')
            print(e)
            log.write(time.asctime()+' An uncaught exception occurred!\n')
            log.write(repr(e)+'\n')
        finally:
            choosetable = []
            log.flush()
except KeyboardInterrupt:
    print(time.asctime(),'Halt')
    log.write(time.asctime()+' Halt\n')
    log.close()
except SystemExit:
    print('test')
