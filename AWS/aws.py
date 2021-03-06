"""
Must do the following:
- EC2:Instances
+ Count number of instances by types
+ Count instances by user
+ List all ec2 instances with info
+ Stop/Start Instances
- List what reservation could be made to optimize cost

- EC2:Volumes
+ List old unused volumes
+ Delete old unused volumes

- ELB
+ List all ELB
+ Get Idle ELB
+ Delete Idle ELB

- RDS
+ List all RDS instance
+ Get Idle RDS
+ Delete Idle RDS

- ALL
+ Get Trusted Advisor infos

- OTHER
+ Generate list of AWS instance type with description
"""

import os
import re
import urllib.request
import ssl
from collections import OrderedDict
import argparse

import boto3
import secret
import ec2
import rds

os.environ["HTTP_PROXY"] = secret.getProxy()
os.environ["HTTPS_PROXY"] = secret.getProxy()

ACCESS_KEY_ID, SECRET_ACCESS_KEY = secret.getAccess()
REGION = secret.getRegion()

SUPPORTC = boto3.client(service_name='support', aws_access_key_id=ACCESS_KEY_ID,
                        aws_secret_access_key=SECRET_ACCESS_KEY, region_name="us-east-1")

#ALL
def getAdvise(verbose):
    """Get Advises from Trusted Advisor"""
    totalSavings = 0
    dreport = {}
    dcategory = {}
    jResp = SUPPORTC.describe_trusted_advisor_checks(language="en")
    for check in jResp["checks"]:
        jResp2 = SUPPORTC.describe_trusted_advisor_check_result(checkId=str(check['id']),
                                                                language="en")
        if 'categorySpecificSummary' in jResp2['result'] and 'costOptimizing' in jResp2['result']['categorySpecificSummary']:
            ditem = {'id':check['id'], 'name':check['name'],
                     'savings':jResp2['result']['categorySpecificSummary']['costOptimizing']['estimatedMonthlySavings']}
            totalSavings += jResp2['result']['categorySpecificSummary']['costOptimizing']['estimatedMonthlySavings']
        else:
            ditem = {'id':check['id'], 'name':check['name']}
        try:
            dcategory[jResp2['result']['status']].append(ditem)
        except:
            dcategory[jResp2['result']['status']] = [ditem]
        dreport[check['category']] = dcategory
    if verbose:
        for k, v in dreport.items():
            for k1, v1 in v.items():
                for it in v1:
                    if 'savings' in it:
                        print(k+":"+k1+":"+it['name']+";"+str(it['savings']))
                    else:
                        print(k+":"+k1+":"+it['name'])
    else:
        for k, v in dreport.items():
            for k1, v1 in v.items():
                if k1 == 'error':
                    for it in v1:
                        if 'savings' in it:
                            print(k+":"+k1+":"+it['name']+";"+str(it['savings']))
                        else:
                            print(k+":"+k1+":"+it['name'])
    return "You can save up to "+str(totalSavings)+"$"

#OTHER
def ignoreCertificate():
    """Simple function to ignore ssl certificate verification"""
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context

def getInstanceTypes():
    """Parse AWS website to list all instance flavors"""
    dflavors = {}
    desc = {"t":"General Purpose",
            "m":"General Purpose",
            "c":"Compute Optimized",
            "x":"Memory Optimized",
            "r":"Memory Optimized",
            "p":"GPU Compute",
            "g":"GPU Instances",
            "f":"FPGA Instances",
            "i":"Storage Optimized",
            "d":"Storage Optimized"}
    url = "https://aws.amazon.com/ec2/instance-types/"
    req = urllib.request.Request(url)
    req.get_method = lambda: 'GET'
    resp = urllib.request.urlopen(req, context=ignoreCertificate())
    data = resp.read().decode('utf-8')
    data = data.split("<h2 id=\"instance-type-matrix\">")[1]
    data = data.split("""</table>
         </div>
        </div>
        <div class="aws-text-box section">""")[0]
    array = data.split("<tr>")
    del array[0]
    del array[0]
    for item in array:
        #remove annoying characters
        item = item.replace("<br />", "")
        item = item.replace("</p>", "")
        try:
            n = item.split("</td>")[0]
            name = re.compile("<td.*>").split(n)[1].strip()
            arr = item.split("</td>")
            mem = re.compile("<td.*>").split(arr[2])[1].strip()
            cpu = re.compile("<td.*>").split(arr[1])[1].strip()
            dflavors[name.replace(".", "_")] = str(name)+" -- "+str(cpu)+\
                                               " vCPU, "+str(mem)+\
                                               " GiB RAM -- "+desc[name[0]]
        except:
            print(item)
    res = OrderedDict(sorted(dflavors.items(), key=lambda t: t[0]))
    return res

if __name__ == '__main__':
    VERBOSE = False
    parser = argparse.ArgumentParser(description="Provide AWS informations using sdk and web site")
    parser.add_argument('-cbt', '--count-by-type', action='store_true',
                        default=False, help='Count ec2 instances for each flavor')
    parser.add_argument('-cbu', '--count-by-user', action='store', dest='user',
                        metavar='<user>', default=False, help='Count ec2 instances for specified user')
    parser.add_argument('-die', '--delete-idle-elb', action='store_true',
                        default=False,
                        help='Delete elb without instances')
    parser.add_argument('-dir', '--delete-idle-rds', action='store_true',
                        default=False,
                        help='Delete RDS instances not used since 14+ days')
    parser.add_argument('-dov', '--delete-old-volumes', action='store_true',
                        default=False,
                        help='Delete volumes that are older than 30 days and unused')
    parser.add_argument('-gf', '--get-flavors', action='store_true',
                        default=False, help='Get list of all available flavors')
    parser.add_argument('-ie', '--idle-elb', action='store_true',
                        default=False, help='Get list of idle elb that can be deleted (no instances)')
    parser.add_argument('-ir', '--idle-rds', action='store_true',
                        default=False, help='Get list of idle rds that can be deleted (14+ days without connection)')
    parser.add_argument('-le', '--list-elb', action='store_true',
                        default=False, help='List all ELB')
    parser.add_argument('-li', '--list-ec2instances', action='store_true',
                        default=False, help='List all ec2 instances')
    parser.add_argument('-lr', '--list-rds', action='store_true',
                        default=False, help='List all RDS instances')
    parser.add_argument('--start-instance', action='store', dest='StartInstanceID',
                        metavar='<instanceId>', default=False, help='Start the specified instance')
    parser.add_argument('--stop-instance', action='store', dest='StopInstanceID',
                        metavar='<instanceId>', default=False, help='Stop the specified instance')
    parser.add_argument('-ta', '--trusted-advisor', action='store_true',
                        default=False, help='Get advice from Trusted Advisor service')
    parser.add_argument('-ov', '--old-volumes', action='store_true',
                        default=False,
                        help='Get a list of volumes that are older than 30 days and unused')
    parser.add_argument('-v', '--verbose', action='store_true',
                        default=False, help='Output will be more verbose')
    dargs = parser.parse_args()
    try:
        if dargs.verbose:
            VERBOSE = True
        if dargs.count_by_type:
            ec2.countInstanceByType(VERBOSE)
        elif dargs.user:
            ec2.getUserInstances(VERBOSE,dargs.user)
        elif dargs.delete_idle_elb:
            ec2.cleanupELB(VERBOSE)
        elif dargs.delete_idle_rds:
            rds.cleanupRDS(VERBOSE)
        elif dargs.delete_old_volumes:
            ec2.cleanupOldUnusedVols(VERBOSE)
        elif dargs.get_flavors:
            resp = ec2.getInstanceTypes()
            for flavorName, details  in resp.items():
                print(flavorName+":"+details)
        elif dargs.idle_elb:
            resp = ec2.getIdleELB(VERBOSE)
            print('\n'.join(resp))
        elif dargs.idle_rds:
            resp = rds.getIdleRDS(VERBOSE)
            print('\n'.join(resp))
        elif dargs.list_elb:
            resp = ec2.listElb(VERBOSE)
            print('\n'.join(resp))
        elif dargs.list_ec2instances:
            ec2.listInstances(VERBOSE)
        elif dargs.list_rds:
            resp = rds.listRds(VERBOSE)
            print('\n'.join(resp))
        elif dargs.StartInstanceID:
            ec2.startInstance(dargs.StartInstanceID)
        elif dargs.StopInstanceID:
            ec2.stopInstance(dargs.StopInstanceID)
        elif dargs.trusted_advisor:
            resp = getAdvise(VERBOSE)
            print(resp)
        elif dargs.old_volumes:
            resp = ec2.getOldUnusedVols(VERBOSE)
            print('\n'.join(resp))
        else:
            parser.print_help()
    except:
        parser.print_help()
