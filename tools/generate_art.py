from pathlib import Path
import re, math
from xml.sax.saxutils import escape
root=Path(__file__).resolve().parent.parent/'webapp'
out=root/'assets'
content=(root/'questions.js').read_text()
scenes=sorted(set(re.findall(r"image:'([^']+)'",content)))

def sign_shape(name):
    # sign symbol sits around x=185 y=175, approximate 140px diameter
    if name=='stop':
        return '<polygon points="185,90 225,107 243,147 226,188 185,204 144,188 128,147 144,107" fill="#db3d4e" stroke="white" stroke-width="9"/><text x="185" y="156" text-anchor="middle" fill="white" font-family="Arial" font-weight="900" font-size="40">STOP</text>'
    if name=='yield':
        return '<polygon points="185,220 113,101 257,101" fill="white" stroke="#d83d4d" stroke-width="12" stroke-linejoin="round"/>'
    if name=='priority':
        return '<rect x="135" y="105" width="100" height="100" fill="white" stroke="#eaf2f6" stroke-width="8" transform="rotate(45 185 155)"/><rect x="145" y="115" width="80" height="80" fill="#f6ca3c" stroke="#f5f7fa" stroke-width="4" transform="rotate(45 185 155)"/>'
    if name=='speed-60':
        return '<circle cx="185" cy="153" r="72" fill="white" stroke="#db3d4d" stroke-width="13"/><text x="185" y="178" font-size="72" font-weight="900" font-family="Arial" text-anchor="middle" fill="#16293c">60</text>'
    if name=='no-entry':
        return '<circle cx="185" cy="153" r="75" fill="#db3d4d" stroke="white" stroke-width="6"/><rect x="131" y="139" width="108" height="28" rx="5" fill="white"/>'
    if name=='roundabout':
        arrows=''.join(f'<path d="M {185+48*math.cos(a):.1f},{155+48*math.sin(a):.1f} l -12,-7 l 5,18 Z" fill="white" transform="rotate({a*180/math.pi+90:.1f} {185+48*math.cos(a):.1f} {155+48*math.sin(a):.1f})"/>' for a in [0,2.09,4.18])
        return '<circle cx="185" cy="155" r="76" fill="#2774b8" stroke="white" stroke-width="7"/><circle cx="185" cy="155" r="44" fill="none" stroke="white" stroke-width="13" stroke-dasharray="85 29"/>'+arrows
    if name=='no-stop':
        return '<circle cx="185" cy="155" r="73" fill="#2266a5" stroke="#de4155" stroke-width="12"/><path d="M135 105L235 205M235 105L135 205" stroke="#e04c58" stroke-width="13"/>'
    if name=='parking':
        return '<rect x="112" y="80" width="146" height="146" rx="12" fill="#1f6da8" stroke="white" stroke-width="7"/><text x="185" y="198" text-anchor="middle" font-size="120" font-family="Arial" font-weight="800" fill="white">P</text>'
    if name=='weight':
        return '<circle cx="185" cy="155" r="75" fill="white" stroke="#dc394e" stroke-width="13"/><text x="185" y="170" text-anchor="middle" font-size="43" font-weight="900" font-family="Arial" fill="#22354a">5 т</text>'
    if name=='height':
        return '<circle cx="185" cy="155" r="75" fill="white" stroke="#db4050" stroke-width="13"/><text x="185" y="168" text-anchor="middle" font-size="43" font-weight="900" font-family="Arial" fill="#22354a">3,5 м</text>'
    if name=='road-work':
        return '<polygon points="185,65 265,145 185,225 105,145" fill="#ffd04f" stroke="#2f3448" stroke-width="7"/><circle cx="185" cy="118" r="13" fill="#27364c"/><path d="M185 134l-15 34m15 -34l24 15m-24 -15l-17 -5m9 35l-19 32m21 -28l22 26" fill="none" stroke="#283349" stroke-width="11" stroke-linecap="round"/>'
    return ''

def car(x=530,y=310,scale=1,color='#f5c65d'):
    return f'<g transform="translate({x} {y}) scale({scale})" filter="url(#shadow)"><ellipse cx="95" cy="110" rx="112" ry="17" fill="#1c314b" opacity=".24"/><path d="M12 60L35 24Q43 11 60 10H128Q150 10 162 28L181 60L190 68Q199 74 199 87V100H0V80Q0 67 12 60Z" fill="{color}"/><path d="M52 20H124Q143 20 153 55H33Z" fill="#a9e4ed" stroke="#e0f5ff" stroke-width="4"/><path d="M91 20V55" stroke="#2b5474" stroke-width="5"/><rect x="6" y="72" width="26" height="14" rx="5" fill="#fff5dc"/><rect x="166" y="72" width="26" height="14" rx="5" fill="#ffe6bd"/><rect x="18" y="90" width="170" height="12" rx="6" fill="#c8a24a"/><circle cx="41" cy="106" r="20" fill="#1d2a40"/><circle cx="41" cy="106" r="9" fill="#8292a8"/><circle cx="158" cy="106" r="20" fill="#1d2a40"/><circle cx="158" cy="106" r="9" fill="#8292a8"/></g>'

def truck(x=490,y=250,scale=1, cargo=False):
    boxes=''.join(f'<rect x="{i*70+10}" y="{-j*40+4}" width="64" height="38" rx="4" fill="#{color}" stroke="#d7ad64" stroke-width="3"/>' for i,color in enumerate(['b7864d','c89a62','a86d3e']) for j in ([1,2] if cargo else []))
    return f'<g transform="translate({x} {y}) scale({scale})" filter="url(#shadow)"><ellipse cx="173" cy="178" rx="208" ry="24" fill="#1c314b" opacity=".20"/>{boxes}<rect x="0" y="36" width="228" height="113" rx="9" fill="#f3f7f5" stroke="#afc3d4" stroke-width="5"/><rect x="10" y="50" width="207" height="71" rx="4" fill="#c9e7df"/><path d="M227 65H291L340 116V151H227Z" fill="#176c91"/><path d="M251 79H284L310 111H251Z" fill="#b2e6f5"/><rect x="221" y="143" width="126" height="17" rx="6" fill="#234961"/><circle cx="70" cy="159" r="27" fill="#192c41"/><circle cx="70" cy="159" r="11" fill="#8c9ca8"/><circle cx="262" cy="159" r="27" fill="#192c41"/><circle cx="262" cy="159" r="11" fill="#8c9ca8"/><rect x="339" y="128" width="15" height="12" rx="3" fill="#ffdd76"/></g>'

def walker(x,y,s=1):
    return f'<g transform="translate({x} {y}) scale({s})"><circle cx="0" cy="-58" r="14" fill="#e2ac83"/><path d="M0 -42L-4 -8M-2 -34L-25 -17M0 -34L20 -15M-4 -8L-25 30M-4 -8L18 29" stroke="#2a4059" stroke-width="12" fill="none" stroke-linecap="round"/><path d="M-13 -45H15L7 -13H-8Z" fill="#ed735e"/></g>'

def scene_svg(name):
    sky='#b9dded' if name not in ('night','fog','rain') else {'night':'#183354','rain':'#7796ac','fog':'#becfd5'}[name]
    background=f'''<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540" role="img" aria-label="Жол ережесіне арналған көрнекі сурет">
<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop stop-color="{sky}"/><stop offset="1" stop-color="#e6f3ed"/></linearGradient><linearGradient id="road" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#637487"/><stop offset="1" stop-color="#374a61"/></linearGradient><linearGradient id="grass"><stop stop-color="#8ac9a5"/><stop offset="1" stop-color="#4d9c80"/></linearGradient><filter id="shadow" x="-25%" y="-25%" width="150%" height="150%"><feDropShadow dx="3" dy="7" stdDeviation="7" flood-color="#15293a" flood-opacity=".25"/></filter><filter id="glow"><feGaussianBlur stdDeviation="10"/></filter></defs>
<rect width="960" height="540" fill="url(#sky)"/>
<circle cx="740" cy="96" r="43" fill="#fff1c1" opacity=".88"/>
<path d="M0 250L70 177 148 246 250 153 346 242 458 165 556 249 674 191 780 253 880 174 960 240V350H0Z" fill="#88b1b3" opacity=".45"/>
<g fill="#72959d" opacity=".53"><rect x="57" y="193" width="55" height="104" rx="3"/><rect x="120" y="225" width="61" height="74" rx="3"/><rect x="798" y="184" width="65" height="115" rx="3"/><rect x="872" y="218" width="61" height="80" rx="3"/></g>
<rect x="0" y="290" width="960" height="250" fill="#83bd9f"/>
<path d="M335 267H610L960 540H0Z" fill="url(#road)"/>
<path d="M335 267L0 540" stroke="#f4f4e0" stroke-width="7" opacity=".85"/><path d="M610 267L960 540" stroke="#f4f4e0" stroke-width="7" opacity=".85"/>
<path d="M468 280L467 304M466 334L463 375M462 417L458 495" stroke="#e9edf0" stroke-width="9" stroke-linecap="round" opacity=".8"/>
<g opacity=".8"><rect x="15" y="275" width="18" height="120" rx="5" fill="#617d70"/><circle cx="22" cy="249" r="45" fill="#5b9b7f"/><circle cx="55" cy="263" r="27" fill="#5e9d81"/><rect x="920" y="270" width="12" height="110" rx="6" fill="#607e6e"/><circle cx="919" cy="250" r="43" fill="#609c7f"/></g>
<g fill="#ffffff" opacity=".35"><rect x="28" y="18" width="120" height="32" rx="16"/><rect x="125" y="30" width="55" height="22" rx="11"/></g>
'''
    tail=''
    if name.startswith('signal-') or name=='signal-dark':
        active={'signal-red':0,'signal-yellow':1}.get(name,-1)
        tail+=f'<rect x="235" y="105" width="16" height="205" rx="8" fill="#34485b"/><rect x="215" y="65" width="55" height="152" rx="17" fill="#202d3e" stroke="#b5c4cb" stroke-width="5"/>'
        for i,color in enumerate(['#e75b4d','#f2c65a','#5fc69a']):
            lit=i==active
            tail+=f'<circle cx="242" cy="{96+i*44}" r="17" fill="{color if lit else "#425663"}" stroke="#1d2835" stroke-width="3"/>'
            if lit:tail+=f'<circle cx="242" cy="{96+i*44}" r="27" fill="{color}" opacity=".23" filter="url(#glow)"/>'
        tail+=car(537,350,0.9)
    elif name in ['stop','yield','priority','speed-60','no-entry','roundabout','no-stop','parking','weight','height','road-work']:
        tail+='<rect x="177" y="218" width="16" height="188" rx="6" fill="#788b8e"/>'+sign_shape(name)
        tail+=truck(488,290,.82) if name in ['weight','height'] else car(540,320,.82)
    else:
        if name=='railway':
            tail+='<path d="M0 400H960" stroke="#987e73" stroke-width="38"/><path d="M0 393H960M0 421H960" stroke="#e3e8e6" stroke-width="8"/><g stroke="#775a52" stroke-width="9">'+''.join(f'<path d="M{x} 378V433"/>' for x in range(20,960,45))+'</g>'
            tail+='<rect x="280" y="194" width="17" height="238" fill="#c9c7c0"/><path d="M289 224L700 315" stroke="#f3f1e6" stroke-width="28"/><path d="M309 227L380 243M425 255L495 269M535 280L605 294M648 300L693 310" stroke="#dc4a54" stroke-width="24"/>'
            tail+='<circle cx="278" cy="198" r="19" fill="#df4d4c"/>'
        elif name in ('crosswalk','turn-ped'):
            for i in range(6):
                yy=390+i*22; tail+=f'<path d="M{200-i*32} {yy}L{723+i*38} {yy}L{750+i*40} {yy+12}L{175-i*29} {yy+12}Z" fill="white" opacity=".9"/>'
            tail+=walker(370,347,1.2)+car(560,312,.7)
        elif name in ['cargo','truck','truck-turn','blind-spot']:
            tail+=truck(430,290,1.12,cargo=(name=='cargo'))
            if name=='blind-spot':
                tail+='<path d="M640 350Q740 304 900 337" fill="none" stroke="#f2ae46" stroke-width="5" stroke-dasharray="15 12"/><ellipse cx="772" cy="360" rx="72" ry="34" fill="#f3b74b" opacity=".23"/>'
            if name=='truck-turn': tail+='<path d="M510 475Q725 430 802 352" stroke="#f8db63" stroke-width="8" fill="none" stroke-dasharray="16 13"/>'
        elif name=='traffic-officer':
            tail+=walker(350,348,1.55)+'<rect x="350" y="260" width="68" height="9" rx="4" fill="#f7f4e8" transform="rotate(-20 350 260)"/>'+car(590,360,.75)
        elif name=='tram':
            tail+='<path d="M450 270L310 540M565 270L680 540" stroke="#d8d2be" stroke-width="8"/><path d="M460 292L542 292 607 415H397Z" fill="#bd454f"/><path d="M470 305H533L558 360H447Z" fill="#bde1eb"/><circle cx="435" cy="400" r="11" fill="#ffe8a8"/><circle cx="574" cy="400" r="11" fill="#ffe8a8"/>'
        elif name=='belt':
            tail+='<rect x="270" y="70" width="450" height="430" rx="100" fill="#26465f"/><rect x="340" y="103" width="300" height="345" rx="80" fill="#7db2c5"/><circle cx="489" cy="192" r="65" fill="#e5ae84"/><path d="M365 386Q381 262 486 275Q598 267 623 386V446H365Z" fill="#eebf57"/><path d="M365 135L580 427" stroke="#273a51" stroke-width="28"/><path d="M365 135L580 427" stroke="#dee5e5" stroke-width="6"/><rect x="550" y="413" width="66" height="36" rx="9" fill="#b74d54"/><rect x="564" y="420" width="25" height="15" rx="4" fill="#dce8ed"/>'
        elif name=='hill':
            tail+='<path d="M80 380Q300 270 475 351Q660 441 890 294" stroke="#f0e8ca" stroke-width="22" fill="none" stroke-dasharray="26 22"/>'+truck(493,305,.85)
        elif name=='fog':
            tail+=car(490,325,.9)
            for i in range(7): tail+=f'<rect x="0" y="{170+i*49}" width="960" height="23" fill="#f1f5f4" opacity=".25"/>'
        elif name=='rain':
            tail+=car(480,318,.97)
            for x in range(30,970,40):
                for y in range(50,540,75):tail+=f'<path d="M{x} {y}l-12 29" stroke="#e5eff9" opacity=".72" stroke-width="3"/>'
        elif name=='night':
            tail+=car(495,305,.95)
            tail+='<path d="M550 386L900 472V520L565 393Z" fill="#ffe7a0" opacity=".25"/><path d="M680 396L890 455V485L689 403Z" fill="#ffe7a0" opacity=".24"/>'
        elif name=='emergency':
            tail+=car(515,313,.97,'#f8f9fa')
            tail+='<rect x="600" y="315" width="44" height="13" rx="4" fill="#e64d4c"/><rect x="612" y="300" width="14" height="44" rx="3" fill="#e64d4c"/><rect x="567" y="306" width="30" height="12" rx="6" fill="#277cd1"/><rect x="639" y="306" width="30" height="12" rx="6" fill="#e9525e"/>'
        elif name=='overtake':
            tail+=car(380,330,.76,'#e6ecf0')+car(590,340,.77,'#f9c967')
            tail+='<path d="M390 460Q485 430 590 451" fill="none" stroke="#f7c765" stroke-width="7" stroke-dasharray="17 13"/>'
        elif name in ('left-turn','right-turn','u-turn','turn-signal'):
            tail+=car(490,320,.95)
            path={'left-turn':'M630 450Q580 370 440 370','right-turn':'M595 455Q700 360 820 362','u-turn':'M660 435C810 264 412 259 430 390','turn-signal':'M620 405Q748 382 822 338'}[name]
            tail+=f'<path d="{path}" stroke="#ffd06f" stroke-width="9" stroke-linecap="round" fill="none" stroke-dasharray="17 13"/>'
        elif name=='equal-intersection':
            tail+='<path d="M0 345H960" stroke="#68798a" stroke-width="109" opacity=".9"/>'+car(460,340,.8,'#eed16f')+car(710,284,.6,'#d65c66')
        elif name in ('lanes','solid-line'):
            tail+=car(530,335,.92)
            if name=='solid-line':tail+='<path d="M465 290L475 540" stroke="white" stroke-width="8"/>'
        elif name=='traffic-jam':
            tail+=car(400,340,.9,'#eac265')+car(630,314,.72,'#e3eaee')+car(545,265,.45,'#da7577')
        elif name=='curve':
            tail+='<path d="M485 277Q700 340 630 540" stroke="#e2d5ae" stroke-width="9" stroke-dasharray="26 17" fill="none"/>'+car(518,337,.84)
        elif name=='reverse':
            tail+=car(510,330,.9)
            tail+='<path d="M520 452L425 452M435 440L419 452 435 464" fill="none" stroke="#ffc75d" stroke-width="8" stroke-linecap="round"/>'
        else:
            tail+=car(515,315,.89)
    if name=='night':
        background=background.replace('fill="#83bd9f"','fill="#476e75"')
    return background+tail+'</svg>'

for name in scenes:
    (out/(name+'.svg')).write_text(scene_svg(name), encoding='utf8')
print('Wrote', len(scenes),'original SVG driving illustrations')
