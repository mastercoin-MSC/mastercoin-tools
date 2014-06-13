#!/usr/bin/python

#######################################################
#                                                     #
#  Copyright Masterchain Grazcoin Grimentz 2013-2014  #
#  https://github.com/grazcoin/mastercoin-tools       #
#  https://masterchain.info                           #
#  masterchain@@bitmessage.ch                         #
#  License AGPLv3                                     #
#                                                     #
#######################################################

import requests
import simplejson
import re
import os
import msc_globals
from msc_utils_bitcoin import *

MAX_COMMAND_TRIES=7
TIMEOUT='timeout -s 9 60 ' 

def get_last_height():
    out, err = run_command(TIMEOUT+"sx fetch-last-height")
    if err != None:
        return err
    else:
        if out.strip()[:3]=='Ass': #assertion failed in mailbox.cpp
            try:
                last_height=requests.get('http://btc.blockr.io/api/v1/block/info/last').json()['data']['nb']
                return last_height
            except Exception,e:
                info(['failed getting height via sx'])
                return '-1'
        return out.strip()

def get_block_timestamp(height):
    if msc_globals.s == False:
        print height
    raw_block, err = run_command(TIMEOUT+"sx fetch-block-header "+str(height))
    if err != None or raw_block == None:
        return (None, err)
    else:
        block_details, err = run_command(TIMEOUT+"sx showblkhead", raw_block)
        if err != None or block_details == None:
            return (None, err)
        else:
            lines=block_details.split('\n')
            if len(lines)>0:
                for line in lines:
                    if line.startswith('timestamp:'):
                        timestamp=int(line.split('timestamp: ')[1])
                        return (timestamp, None)
                else:
                    return (None, "empty block details")

def get_raw_tx(tx_hash):
    out, err = run_command(TIMEOUT+"sx fetch-transaction "+tx_hash)
    if err != None:
        return err
    else:
        return out

def get_json_tx(raw_tx, tx_hash='unknown hash'):
    if raw_tx != None and raw_tx.strip()[:3]=='Ass': #assertion failed in mailbox.cpp
        if tx_hash!='unknown hash':
            info('assertion failed, retry to get '+tx_hash)
            raw_tx=get_raw_tx(tx_hash)
        else:
            error('assertion failed, no tx_hash provided')
    parsed_json_tx=None
    for i in range(MAX_COMMAND_TRIES): # few tries
        json_tx, err = run_command(TIMEOUT+"sx showtx -j", raw_tx)
        if err != None or json_tx == None:
            if i == MAX_COMMAND_TRIES:
                error(str(json_tx)+' '+str(tx_hash))
        else:
            try:
                parsed_json_tx=simplejson.JSONDecoder().decode(json_tx)
                break
            except simplejson.JSONDecodeError:
                if i == MAX_COMMAND_TRIES:
                    error(str(json_tx)+' '+str(tx_hash))
    return parsed_json_tx

def get_tx(tx_hash):
    raw_tx=get_raw_tx(tx_hash)
    return get_json_tx(raw_tx, tx_hash)

def get_tx_index(tx_hash):
    out, err = run_command(TIMEOUT+"sx fetch-transaction-index "+tx_hash)
    if err != None:
        info(err)
        return (-1, -1)
    else:
        try:
            s=out.split()
            height=s[1]
            index=s[3]
            if height=='failed:':
		url='http://btc.blockr.io/api/v1/tx/info/' + tx_hash
                if msc_globals.s == False:
                    print url
                try:
                    height=requests.get(url).json()['data']['block']
                    return(height,-1)
                except Exception,e:
                    info(['failed getting height for '+tx_hash,e])
                    return (-1,-1)
	    else:
                return(height,index)
	except IndexError:
            return (-1,-1)

def get_json_history(addr):
    out, err = run_command(TIMEOUT + "sx history -j "+addr)
    if err != None:
        return err
    else:
        return out

def get_history(addr):
    parsed_json_history=None
    json_history=get_json_history(addr)
    try:
        parsed_json_history=simplejson.JSONDecoder().decode(json_history)
    except simplejson.JSONDecodeError:
        error('error parsing json_history')
    return parsed_json_history

# used as a key function for sorting history
def output_height(item):
    return item['output_height']

def get_value_from_output(tx_and_number):
    try:
        txid=tx_and_number.split(':')[0]
        number=int(tx_and_number.split(':')[1])
    except IndexError:
        return None
    rawtx=get_raw_tx(txid)
    json_tx=get_json_tx(rawtx)
    if json_tx == None:
        try:
            #to satoshi
            req=requests.get( 'http://btc.blockr.io/api/v1/tx/info/' + tx_hash )
            requestJson = req.json()
            value=float(requestJson['data']['vouts'][number]['amount'])*100000000
            return int(value) #back to satoshi
        except Exception,e:
            info(['failed getting json_tx (None) for '+txid,e])
            return None
    try:
        all_outputs=json_tx['outputs']
    except TypeError: # obelisk can give None
        info('bad outputs parsing on: '+json_tx)
        return None
    output=all_outputs[number]
    return output['value']

def get_address_from_output(tx_and_number):
    try:
        tx_hash=tx_and_number.split(':')[0]
        number=int(tx_and_number.split(':')[1])
    except IndexError:
        return None
    rawtx=get_raw_tx(tx_hash)
    json_tx=get_json_tx(rawtx)
    if json_tx == None:
       try:
            address=str(requests.get('http://btc.blockr.io/api/v1/tx/info/' + tx_hash).json()['data']['vouts'][number]['address'])
            return address
       except Exception,e:
            info(['failed getting json_tx (None) for '+txid,e])
            return None
    all_outputs=json_tx['outputs']
    output=all_outputs[number]
    return output['address']

def get_vout_from_output(tx_and_number):
    try:
        txid=tx_and_number.split(':')[0]
        number=int(tx_and_number.split(':')[1])
    except IndexError:
        info('index error')
        return None
    rawtx=get_raw_tx(txid)
    json_tx=get_json_tx(rawtx)
    if json_tx == None:
        info('failed getting json_tx (None) for '+txid)
        return None
    try:
        all_outputs=json_tx['outputs']
    except TypeError: # obelisk can give None
        info('bad outputs parsing on: '+json_tx)
        return None
    output=all_outputs[number]
    return output

def get_pubkey(addr):
    out, err = run_command(TIMEOUT+"sx get-pubkey "+addr)
    if err != None:
        return err
    else:
        return out.strip('\n')

def pubkey(key):
    out, err = run_command(TIMEOUT+"sx pubkey ",key)
    # the only possible error is "Invalid private key."
    if out.strip('\n') == "Invalid private key.":
        return None
    else:
        return out.strip('\n')

def get_utxo(addr, value):
    out, err = run_command(TIMEOUT+"sx get-utxo "+addr+" "+str(value))
    if err != None:
        return err
    else:
        return out

def get_balance(addrs):
    out, err = run_command(TIMEOUT+"sx balance -j "+addrs)
    if err != None:
        return err
    else:
        try:
            parsed_json_balance=simplejson.JSONDecoder().decode(out)
        except simplejson.JSONDecodeError:
            error('error parsing balance json of '+addrs)
        return parsed_json_balance

def rawscript(script):
    out, err = run_command(TIMEOUT+"sx rawscript "+script)
    if err != None:
        return err
    else:
        return out.strip('\n')

def mktx(inputs_outputs):
    out, err = run_command(TIMEOUT+"sx mktx "+inputs_outputs, None, True)
    # ignore err
    return out

def get_addr_from_key(key): # private or public key
    out, err = run_command(TIMEOUT+"sx addr ", key)
    return out.strip('\n')

def sign(tx, priv_key, inputs):
    info('signing tx')
    addr=get_addr_from_key(priv_key)
    hash160=bc_address_to_hash_160(addr).encode('hex_codec')
    prevout_script=rawscript('dup hash160 [ '+hash160 + ' ] equalverify checksig')
    # save tx to a temporary file
    # FIXME: find a more secure way that does not involve filesystem
    f=open('txfile.tx','w')
    f.write(tx)
    f.close()
    try:
        # assumtion: that all inputs come from the same address (required in spec)
        n=0;
        for i in inputs:
            signature=run_command(TIMEOUT+'sx sign-input txfile.tx '+str(n)+' '+prevout_script, priv_key)[0].strip('\n')
            signed_rawscript=rawscript('[ '+signature +' ] [ '+pubkey(priv_key)+' ]')
            signed_tx=run_command(TIMEOUT+'sx set-input txfile.tx '+str(n), signed_rawscript)
            n+=1
            # replace the file with the signed one
            f=open('txfile.tx','w')
            f.write(signed_tx[0].strip('\n'))
            f.close()
    except IndexError:
        error('failed parsing inputs for signing')
    return signed_tx[0].strip('\n')

def validate_sig(filename, index, script_code, signature):
    out, err = run_command(TIMEOUT+'sx validsig '+filename+' '+str(index)+' '+script_code+' '+signature)
    if err != None:
        return err
    else:
        return out

def validate_tx(filename):
    out, err = run_command(TIMEOUT+'sx validtx ' + filename)
    if err != None:
        return err
    else:
        out = out.strip('\n')
        info('validated')
        info(out)
        found_success = re.findall("Success|input not found",out)
        if len(found_success) != 0:
            return None
        else:
            return out

def send_tx(filename, host='localhost', port=8333):
    out, err = run_command(TIMEOUT+"sx sendtx "+filename+' '+host+' '+port)
    if err != None:
        return err
    else:
        info('sent')
        return None

def broadcast_tx(filename):
    out, err = run_command(TIMEOUT+"sx sendtx-obelisk " + filename)
    if err != None:
        return err
    else:
        out = out.strip('\n')
        info('broadcasted')
        info(out)
        found_success = re.findall("Success",out)
        if len(found_success) != 0:
            return None
        else:
            return out
