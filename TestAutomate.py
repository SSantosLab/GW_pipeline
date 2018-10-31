import subprocess, os
from threading import Thread
import make_recycler_config
import argparse
import numpy as np
import smtplib
from email.mime.text import MIMEText

############# 8/14/18 update #############
### This scirpt is still a work in    ###
### progress. To run as is, make sure ###
### to run in a the directory that    ### 
### Main-Injector, gw_workflow, ,and  ###
### Post-Processing live.             ###
#########################################

cwd = os.getcwd()
parser = argparse.ArgumentParser()
parser.add_argument('--rootdir',
                    default = cwd,
                    help="Directory where the Main-Injector, gw_workflow, and PostProcessing directories live.")

args=parser.parse_args()

DIR_SOURCE = args.rootdir
#DIR_MAIN = DIR_SOURCE.rsplit('/', 1)[0]

#DIR_PLOTS = DIR_MAIN+'/plots/'
#DIR_OUT = DIR_MAIN+'/out/'


############# Send emails to appropriate people when things fail #############

def send_email(error, where):
    
    text = 'There was an error with the GW pipeline during %s, with message %s ' % (where, error)
    msg = MIMEText(text)
    # me == the sender's email address
    # you == the recipient's email address
    me = 'alyssag94@brandeis.edu'
    you = 'alyssag94@brandeis.edu'
    msg['Subject'] = 'GW pipeline error'
    msg['From'] = me            
    msg['To'] = you
    s = smtplib.SMTP('localhost')
    s.sendmail(me, [you], msg.as_string())
    print('There was an error. An email was sent to %s' % you)
    s.quit()


############# Use to update current environment because subprocess is shit #############

def source(script, update=1):
    pipe = subprocess.Popen(". %s > /dev/null; env" % script, stdout=subprocess.PIPE, shell=True)
    data = pipe.communicate()[0]
    env={}
    for line in data.splitlines():
        #print(line)
        splt1=line.split('=',1)
        if splt1[0] == 'BASH_FUNC_setup()':
            splt1[1] = '() {  eval `$EUPS_DIR/bin/eups_setup           "$@"`  \n}'
            #print(splt1[1])
        if splt1[0] == 'BASH_FUNC_unsetup()':
            splt1[1] = '() {  eval `$EUPS_DIR/bin/eups_setup --unsetup "$@"`  \n}'
            #print(splt1[1])
        if splt1[0] == 'BASH_FUNC_module()':
            splt1[1]='() {  eval `/usr/bin/modulecmd bash $*`   \n}'
            #print(splt1[1])
        if splt1[0] =='}':
            continue

        #print(splt1)
        env[splt1[0]]=splt1[1]
        
    if update:
        os.environ.update(env)

    return env

"""
############# Make yaml file for recycler ############# 

#information needed to make the .yaml config file for recycler
parser.add_argument('--camera', 
                    choices=['decam', 'hsc'], 
                    default='decam', 
                    help="what camera did we use, default=decam")
parser.add_argument('--res', 
                    type=str, 
                    choices=[64, 128, 256], 
                    default=128,
                    help="what resolution do you want the map, default=128")
parser.add_argument('--debug', 
                    type=str, 
                    choices=[True,False], 
                    default=False, 
                    help="turn debugging on/off")
parser.add_argument('--propid', 
                    default='2017B-0110', 
                    help='proposal id for this run')

#makeYaml takes (camera, res, propid, sendEmail=(default False), sendTexts=(default False), debug=(default False)) 
yamlName= make_recycler_config.makeYaml(camera=args.camera, res=args.res, propid=args.propid, debug=args.debug)

#this is a hack to make sure the true/false statements are capitalized.
os.system("sed -i -e 's/false/False/g' "+yamlName)
os.system("sed -i -e 's/true/True/g' "+yamlName)

#need this to live in the production directory
os.system(str("mv ")+yamlName+str(" "+DIR_SOURCE+"/Main-Injector/"))


############# Main Injector #############

#not sure what kind of trigger will come from listener but something needs to be triggered here to start
#Add the make_recycler_config.py here or at the end of main injector? 

mainoutfile= open('test_main.out', 'w')
mainerrfile = open('test_main.err','w')

source(DIR_SOURCE+'/Main-Injector/SOURCEME')
print("Environment successfully set up for Main Injector")


start_main = subprocess.Popen(['python', DIR_SOURCE+'/Main-Injector/recycler.py'], 
                        stderr=subprocess.PIPE, stdout=subprocess.PIPE, cwd=DIR_SOURCE+'Main-Injector/')

main_out, main_err = start_main.communicate()

mainoutfile.write(main_out)
mainerrfile.write(main_err)
mainoutfile.close()
mainerrfile.close()

rc = start_main.returncode

print('The return code for recycler is '+str(rc))
if rc != 0:
    error = open(mainoutfile.name, 'r')
    err_msg = error.readlines()
    error.close()
    where = "Main Injector ("+DIR_SOURCE+"/"+mainoutfile.name+")"
    send_email(err_msg, where)

print('')
print("Finished recycler for main injector. Visit website for skymaps")
print('')
print("Moving on to image processing ...")
print('')

"""
############# Image Processing ################ 

############ create new season number ###########
### Y6 will start with 600 (417 for mock)   #####
import easyaccess
import fitsio

query = 'SELECT max(SEASON) from marcelle.SNFAKEIMG where SEASON < 800;'
connection=easyaccess.connect('destest')
connection.query_and_save(query,'testfile.fits')
data = fitsio.read('testfile.fits')
print(data[0][0])

newseason = (int(data[0][0]/100) + 1)*100
print("the season number for this event is "+str(newseason))
print('')

### make config file for dagmaker ###
###       THIS NEEDS HELP         ###

#import make_dagrc
#make_dagrc.makeDagRC(season=newseason)
#dagrc_name= make_dagrc.makeDagRC(seasonval=417) #for mock run
#os.system('mv dagmaker.rc gw_workflow/dagmaker.rc') 

############################################################
"""
# diffimg_setup + seasonCycler has structure to make the exposure list
# Need to modify to get just what we want here -- curatedExposure.list

source(DIR_SOURCE+'/Post-Processing/diffimg_setup.sh')
os.system('. '+DIR_SOURCE+'/seasonCycler.sh') #find new exposures and create list
"""


source('gw_workflow/setup_img_proc.sh')
print("Environment successfully set up for Image processing.")
print('')

explist = np.genfromtxt(DIR_SOURCE+'/gw_workflow/bns_nite1_first10exposures.list', delimiter=' ', usecols=0) #this will just be curatedExposure.list for production. new_curated.list

imgprocout = open('test_imgproc.out', 'w')
imgprocerr = open('test_imgproc.err', 'w')

for i in explist:
    EXPNUM = int(i)
    check = os.path.isdir(DIR_SOURCE+'/gw_workflow/mytemp_'+str(EXPNUM))

    check = False #only for test runs
    if check == False:
        print("mytemp_"+str(EXPNUM)+" does not exist, running DAGMaker.sh")

        img1 = subprocess.Popen(['bash','-c', DIR_SOURCE+'/gw_workflow/DAGMaker.sh '+str(EXPNUM)] ,
                                stdout = subprocess.PIPE, stderr=subprocess.PIPE, cwd='gw_workflow/') 
        
        im1out, im1err = img1.communicate()
        imgprocout.write(im1out)
        imgprocerr.write(im1err)

        rc1 = img1.returncode
        print('The return code for DAGMaker is '+str(rc1))
        
        if rc1 != 0:
            err_msg = "DAGMaker failed."
            where = "Image Processing ("+DIR_SOURCE+"/"+imgprocout.name+")"
            send_email(err_msg, where)
        else:
            print('Finished ./DAGMaker for exposure '+str(EXPNUM)+'. Submitting jobs.')

        print('')

        img2 = subprocess.Popen(['jobsub_submit_dag','--role=DESGW', '-G', 'des','file://desgw_pipeline_'+str(EXPNUM)+'.dag'], 
                                stdout = subprocess.PIPE, stderr=subprocess.PIPE, cwd='gw_workflow/')        

        im2out, im2err = img2.communicate()
        imgprocerr.write("Errors for jobsub_submit_dag:\n")
        imgprocout.write("Output for jobsub_submit_dag:\n")
        imgprocout.write(im2out)
        imgprocerr.write(im2err)

        rc2 = img2.returncode
        print('The return code for this jobsub is '+str(rc2))
        if rc2 != 0:
            err_msg = "Image processing job sub failed."
            where = "Image Processing ("+DIR_SOURCE+"/"+imgprocout.name+")"
            send_email(err_msg, where)

        else:
            print('Finished jobsub_submit_dag for exposure '+str(EXPNUM))
            print('')
            print('Look at test_imgproc.out for the jobid')
    else:
        print('Already processed exposure number '+str(EXPNUM))
imgprocout.close()
imgprocerr.close()

print("Finished image processing! Moving on to post processing...")
print('')
print('')


############# Run Post Processing #############
############# we have a script that will make the postproc_seasonnumber.ini 
############# just need to know where to look for the ligo id 

postprocout = open(DIR_SOURCE+'/test_postproc.out', 'w')
postprocerr = open(DIR_SOURCE+'/test_postproc.err', 'w')
#print("Environment successfully set up for post processing.")

#import yaml
#with open('/data/des41.a/data/desgw/alyssa_test/Main-Injector/recycler.yaml') as f:
#    var=yaml.load(f.read())

#os.system('python Post-Processing/make_postproc_ini.py --season '+str(var['season']))

start_pp = ['bash','-c', DIR_SOURCE+'/Post-Processing/seasonCycler.sh']
postproc = subprocess.Popen(start_pp, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd='Post-Processing/')

while postproc.poll() is None:
    l = postproc.stdout.readline()
    print l

postproc_out, postproc_err = postproc.communicate()
rc3 = postproc.returncode

postprocout.write(postproc_out)
postprocerr.write(postproc_err)

postprocout.close()
postprocerr.close()

print('the return code for post processing is '+str(rc3))
print('')

if rc3 != 0: 
    error = os.popen('tail -10 '+postprocerr.name).read()
    where = "Post Processing ("+DIR_SOURCE+"/"+postprocerr.name+")"
    send_email(error, where)
    
print("Finished Post-Processing! Visit website for more information")





