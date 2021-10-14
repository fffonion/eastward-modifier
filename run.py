#!/usr/bin/env python3
#  coding: utf-8
import os
import sys
import time
import zlib
import argparse
import msgpack
import whirlpool
import hashlib

key = b"EW"

def load(path):
    with open(path, "rb") as f:
        packed = f.read()
        h = packed[:64]
        d = packed[64:]
        w = whirlpool.new(d)
        w.update(key)
        if w.digest() != h:
            raise ValueError("game save is broken")
        # ignore headers
        d = zlib.decompress(d, -15)
        d = msgpack.unpackb(d, strict_map_key=False, raw=True)
        return d

def save(path, data):
    with open(path, "wb") as f:
        packed = msgpack.packb(data, use_bin_type=False)
        # skip header and trailer
        packed = zlib.compress(packed)[2:-4]
        w = whirlpool.new(packed)
        w.update(key)
        h = w.digest()
        f.write(h)
        f.write(packed)

def print_info(gamesave):
    #print(gamesave.keys())
    print("SAVE INFO")
    print("=" * 32)
    print(time.strftime("Save time: %Y-%m-%d %X", time.localtime(gamesave[b'info'][b'time'])))
    pd = gamesave[b'info'][b'playerData']
    def hms(t):
        return "%02d:%02d:%02d" % (t//3600, (t%3600)//60, t%60)
    print("Play time: %s" % hms(pd[b'playtime']))
    print("Chapter: %s" % pd[b'chapter'])
    print("Health: %s%s" % ("♥" * (pd[b'health']//10), "♡" * ((pd[b'max_health'] - pd[b'health'])//10)))
    print("Money: %d" % gamesave[b'data'][b'player{version=0}'][b'data'][b'stat'][b'money'])

BACK = "BACK"
false = False
true = True
def printable(l, k):
    v = l[k]
    if isinstance(v, dict) or isinstance(v, list):
        v = "<enter>"
    elif isinstance(v, bytes):
        v = v.decode('ascii')
    if isinstance(l, dict):
        return "%-24s: %s" % (k.decode('ascii'), v)
    else:
        return "%s" % v

def menu(l, prefix="", maxitems=20):
    index = 0
    if isinstance(l, dict):
        items = list(l.keys())
    else:
        items = list(range(len(l)))

    print_list = True
    while True:
        if print_list and index < len(l):
            print("..  <go back>")
            print("\n".join(["%d: %s" % (i+1, printable(l, items[i])) for i in range(index, min(len(l), index+maxitems))]))
            if index+maxitems < len(l):
                print("...")
        print_list = False
        
        sel = input("[%s] select > " % (prefix))
        if sel.isnumeric() and 0 < int(sel) <= len(l):
            kk = items[int(sel)-1]
        elif sel == "q" or sel == "s":
            return sel == "s"
        elif sel == "" or sel == '\x1b[B':
            if index < len(l):
                index += maxitems
                print_list = True
            continue
        elif sel == '\x1b[A':
            index = max(index - maxitems, 0)
            print_list = True
            continue
        elif sel == "l":
            print_list = True
            continue
        elif sel == "..":
            return BACK
        elif sel.encode('ascii') in l:
            kk = sel.encode('ascii') 
        else:
            continue

        kkd = kk.decode('ascii') if isinstance(kk, bytes) else kk
        vv = l[kk]
        if isinstance(vv, dict) or isinstance(vv, list):
            r = menu(vv, prefix="%s.%s" % (prefix, kkd), maxitems=maxitems)
            if r != BACK:
                return r
            else:
                continue
        
        vi = input("Update %s.%s (%s) to? > " % (prefix, kkd, vv))
        if not isinstance(vv, bytes):
            vi = eval(vi)
        l[kk] = vi
        print("Updated!")
        print_list = True


def modify_info(d):
    print("EDIT INFO")
    print("enter s to save and q to quit")
    print("=" * 32)
    return menu(d, "data")

 
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', dest="input", help = "save file path")
    parser.add_argument('--info_only', action='store_true', default=False,
                        help="display basic info")
    parser.add_argument('--minirpg', action='store_true', default=False,
                        help="modify earthborn rpg")
    args = parser.parse_args()

    save_path = args.input
    gamesave = load(save_path)
    
    print_info(gamesave)

    if args.info_only:
        os.exit(0)

    with open(save_path, "rb") as f:
        with open(save_path + ".bak", "wb") as f2:
            f2.write(f.read())
    print("Backup written to " + save_path + ".bak")

    if args.minirpg:
        dd = gamesave[b'data'][b'minirpg{version=0}'][b'data'][b'data']
    else:
        dd = gamesave[b'data'][b'player{version=0}'][b'data']
    if modify_info(dd):
        save(save_path, gamesave)
        print("Saved written to " + save_path + ".bak")
    else:
        print("Save aborted")
