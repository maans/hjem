"""Reviewed PDF chord transcriptions. Bars are explicit; no melody is fabricated.

One harmonic cycle is for practice. Concert solos and cues remain on each work.
Tokens without durations share a bar equally. {meter} changes apply immediately.
"""
import json,re
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'research/helles'
charts=[]
def add(title,key,tempo,style,pdf,sections,meter='4/4',note='',config=None):
    charts.append(dict(title=title,key=key,tempo=tempo,style=style,pdf=pdf,sections=sections,meter=meter,note=note,config=config))

add('Autumn Leaves','Cm',138,'Swing','autumn-leaves-leadsheet.pdf',[
 ('A1','Fm7|Bb7|Ebmaj7|Abmaj7|Dm7b5|G7b9|Cmmaj7|Cmmaj7'),
 ('A2','Fm7|Bb7|Ebmaj7|Abmaj7|Dm7b5|G7b9|Cmmaj7|Cmmaj7'),
 ('B','Dm7b5|G7b9|Cmmaj7|Cmmaj7|Fm7|Bb7|Ebmaj7|Abmaj7'),
 ('C','Dm7b5|G7b9|Cmmaj7 F9b5|Bbm7 Eb7b5|Abmaj7|Dm7b5 G7#5|Cmmaj7|Cmmaj7')])
add('All The Things You Are','Eb',138,'Swing','all-the-things-you-are-leadsheet.pdf',[
 ('A1','Cm7|Fm7|Bb7|Ebmaj7|Abmaj7|Am7 D7|Gmaj7|Gmaj7'),
 ('A2','Gm7|Cm7|F7|Bbmaj7|Ebmaj7|Em7b5 A7|Dmaj7|Dmaj7'),
 ('B','Em7|A7|Dmaj7|Dmaj7|C#m7b5|F#7|Bmaj7|G7#5'),
 ('A3','Cm7|Fm7|Bb7|Ebmaj7|Abmaj7|Db7|Gm7|F#dim7|Fm7|Bb7|Ebmaj7|Dm7b5 G7#9')],note='Grundform 36 takter; den overstregede intro er udeladt. Intro kan spilles fra de sidste fire takter.')
add('Brevet','Dm',66,'Ballad','brevet-leadsheet.pdf',[
 ('Vers 1','Dm C/E F|Bbmaj7:2 C:2|A7/C#|Bb/D C/E F|Bbmaj7:2 C:2|A7|Gm Dm/F|C/E Dm'),
 ('Vers 2','Dm C/E F|Bbmaj7:2 C:2|A7/C#|Bb/D C/E F|Bbmaj7:2 C:2|A7|Bb F/A|Gm7 C'),
 ('Mellemstykke','F|{2/4}Csus4 C|{4/4}Bb/D C/E F Bb|Bdim7|{2/4}C|{4/4}A7/C# Dm C/E Cdim7/F# D'),
 ('Videre','{3/4}Ebdim7:1 Em:2|{4/4}C D Em Am7 D|Esus4:1 Em:2 D/F#:1|G|{2/4}D|{4/4}C/E D/F# G Cdim7 A7/C#|{2/4}D'),
 ('Modulation','{4/4}B/D# Em F#dim7 Ddim7/G# E7|{3/4}Fdim7:1 F#m:2|{4/4}D E F#m Bm7 E|F#sus4 F#m|F#m/E:1 D:2 G/D:1|A/D G/D|D G/D|Gm6/D'),
 ('Tilbage','Bb/D C/E F Bb Bdim7|{3/4}C#dim7:1 Dm:2|{4/4}Bb C Dm Gm7 C|Dsus4 Dm')],note='Blandet 4/4, 2/4 og 3/4 og modulationer følger nodearket. Grundformen slutter før D.S.; koncertgentagelser vælges efter aftalerne.')
add('Dansevise','Am',160,'Jazz waltz','dansevise-leadsheet.pdf',[
 ('A1','Am7|D7|Am|D7|Am|D7|Am|Am|C|Am|F|Am|F7|F7|Bm|E7'),
 ('A2','Am7|D7|Am|D7|Am|D7|Am|Am|C|Am|F|Am|F7|E7 Am G|Am|Am'),
 ('B','Dm|Dm|G7|C|Am|F7|F7|Am|F|F|G7|C|Am|F7|F7|Am D7'),
 ('A3','Am|D7|Am|D7|Am|D7|Am|Am|C|Am|F|Am|F7|E7 Am G'),
 ('Vamp','Am|G|Am|G|Am|G|Am|G|Am|G|Am|Am|Dm|Dm|Dm|Dm|Am|G|Am|Am'),
 ('B2','Dm|G7|C|Am F|G7|C|Am|Dm|E7|Am|Am7|Dm|Dm|Dm/E|Dm/E|E7|E7'),
 ('Coda','Am|G|Am|G|Am|Am|Am|Am')],meter='3/4',note='A/B, vamp og coda efter PDF. Rubato i coda styres manuelt; akkompagnementet holder det valgte tempo.')
add('Deidres Samba','Cm',72,'Samba','deidres-samba-leadsheet.pdf',[
 ('Vers','Cm6 Cm6/G|Ddim7/Ab|G7 G7/B|Cm6|Fm7|Bb7|Fm7 Bb7|Eb G7/D|Cm Cm/Bb|Adim7|D7|G7|Cm|Cm7 Fm Cm|Ddim7 F#dim7|G7|G7'),
 ('Omkvæd','C6|C6|C6|C6 F6|F6|F6|C6'),
 ('Refræn 1','C7|F6|Dm7 G7|C6'),
 ('Refræn 2','C7|F6|Dm7 G7|C')],note='Mollvers og duromkvæd efter PDF; sidste refræn afrundes på C. Tempo 72 følger Helles’ aftaler.')
add('Dejlighedssang','Bb',88,'Ballad','dejlighedssang-leadsheet.pdf',[
 ('Vers','Eb6 Bb/D|F/A Gm|D D7/F#|Gm Gm/F|Ebmaj7|Dm Eb|Cm7|Eb F|{2/4}F|{4/4}Ebm|Gm7|Cm:2 F7:2|Bbsus4 Bb')],note='Klingende B♭: svarer til G-greb med capo III / A-greb med capo I. Helles’ øvetempo 88 bevares; PDF angiver 95.')
add('Har du visor, min vän','Dm',120,'Jazz waltz','har-du-visor.pdf',[
 ('A','Dm|Am7|Dsus4|D7|Gm|Gm/Bb|G#dim7|A|Bbmaj7|Am7:1 Dsus4:2|Dm|Dm'),
 ('B','Gm7|C7|Fmaj7|Bbmaj7|Gm/E|A7|G#dim7|A|Dm:2 Dm/C:1|Gm/Bb|D7/A|Gm|Dm/A:2 Am7:1|Dsus4|Dm|Dm')],meter='3/4',note='PDF angiver cirka 110–130; afspilningen begynder ved 120. Optakt er udeladt i akkordgrundformen.')
add('Hvorfor er lykken så lunefuld','Fm',54,'Ballad','hvorfor-er-lykken-sa-lunefuld-leadsheet.pdf',[
 ('Vers / intro','Fm|Cm|Fm|Cm|Fm6|G7|Fm6|G7|C7|Fm C7|Db7|C7b9'),
 ('A1','Fm C7/G|Fm/Ab F7/A|Bbm F7/C|Bbm/Db G7|C7b9|C7b9|Fm C7|Fm C7'),
 ('A2','Fm C7/G|Fm/Ab F7/A|Bbm F7/C|Bbm/Db G7|C7b9|C7b9|Fm C7|Fm'),
 ('B','F7|Bbm|F7|Bbm|G7|Cm G7|C7b9|C7b9'),
 ('A3','Fm C7/G|Fm/Ab F7/A|Bbm F7/C|Bbm/Db G7|C7b9|C7b9|Fm C7|Fm')],note='Vers/intro og AABA efter begge PDF-sider. De trykte basomvendinger er bevaret.')
add('Nature Boy','Dm',108,'Bossa nova','nature-boy-leadsheet.pdf',[
 ('A','Dm|Em7b5 A7|Dm|Em7b5 A7|Dm Dmmaj7|Dm7|Dm6 Gm6|Dm|Em7b5|A7|A7|Dm|Dm|E7b9|E7b9|A7|A7'),
 ('B','Dm|Em7b5 A7|Dm|Em7b5 A7|Dm Dmmaj7|Dm7|Dm6 Gm6|Dm|Em7b5|A7|A7|Dm|Bm7b5|E7b9|A7b9|Dm|Em7b5 A7')],note='PDF’ens udskrevne A/B-forløb med udvidet slutfrase. Latinpræg fra Helles’ node; bossa bruges som øveakkompagnement.')
add("'Round Midnight",'Cm',60,'Slow jazz ballad','round-midnight-leadsheet.pdf',[
 ('A1','Cm Am7b5|Dm7b5 G7#5|Cm7 F7|Abm7 Db7 Gm7 C7|Fm Bb7|Cm F7|Ab7|G7'),
 ('A2','Cm Am7b5|Dm7b5 G7#5|Cm7 F7|Abm7 Db7 Gm7 C7|Fm Bb7|Cm F7|Ab7 G7|Cm7'),
 ('B','Am7b5 D7b9|G7|Am7b5 D7b9|G7|Fm7:1 Bb7:1 Ebmaj7:2|Ab7 G7|C7 Bb7|Ab7 G7'),
 ('A3','Cm Am7b5|Dm7b5 G7#5|Cm7 F7|Abm7 Db7 Gm7 C7|Fm Bb7|Cm F7|Ab7|G7|Cm')])
add('Quiet Night of Quiet Stars','Bb',63,'Bossa nova','quiet-night-of-quiet-stars-leadsheet.pdf',[
 ('A1','C7/G|C7/G|Gbdim7|Gbdim7|Fm7|Bb7sus4 Ebmaj7|Ebdim7/A Ebmaj7/Bb|Ebmaj7/Bb'),
 ('B','Ebm7|Ab7|Dm7b5|G7#5|C7|C7|Cm7|Gbdim7'),
 ('A2','C7/G|C7/G|Gbdim7|Gbdim7|Fm7|Bb7sus4 Ebmaj7|Ebdim7/A Ebmaj7/Bb|Ebmaj7/Bb'),
 ('C','Ebm7|Ab7|Dm7b5|Gm7|Cm7|F7|Dm7b5|G7#5|Cm7|F7|Bb6|Bb6')],note='A–B–A–C efter Helles’ PDF, inklusive slutforlængelsen. Tempo 63 følger den noterede puls.')
add('There Will Never Be Another You','C',152,'Swing','there-will-never-be-another-you-leadsheet.pdf',[
 ('A1','Cmaj7|Cmaj7|Bm7b5|E7|Am|Am|Gm9|C9|Fmaj7|Bb9#11|Cmaj7|Am7|D9|D9|Dm7|G7'),
 ('A2','Cmaj7|Cmaj7|Bm7b5|E7|Am|Am|Gm9|C9|Fmaj7|Bb9#11|Cmaj7|F#m7b5 B7|C6 F9#11|Em7 A7|Dm7 G13|C6')])
add('This Masquerade','Bbm',108,'Bossa nova','this-masquerade-leadsheet.pdf',[
 ('A1','Bbm|Bbmmaj7|Bbm7|Eb13|Bbm7|Gb9|Cm7|F7#5'),
 ('A2','Bbm|Bbmmaj7|Bbm7|Eb13|Gb7|F7#5|Bbm7|Bbm7'),
 ('B','Abm7|Db13b9|Gbmaj7|Gbmaj7|Abm7|Db13b9|Gbmaj7|Gbmaj7|Gm7|C13 C7#5|Fmaj7|Fmaj7 G7|Cm7|C13 C7#5|F9sus4|F9sus4'),
 ('A3','Bbm|Bbmmaj7|Bbm7|Eb13|Bbm7|Gb9|Cm7|F7#5|Bbm7|Bbm7')],note='AABA med udskrevet 16-takters B. Den sidste A afrundes på B♭m; intro/outro-vamp findes i spilleaftalerne.')
add('What It Means To Me','Cm',60,'Ballad','what-it-means-to-me-leadsheet.pdf',[
 ('A1','Cm7|Gm7|Abadd2|Bb11|Eb|Eb/G|Abadd2|Bb11'),
 ('A2','Cm7|Gm7|Abadd2|Bb11|Eb|Eb/G|Am11|D7'),
 ('B','Gmaj7|Cmaj7|F#dim7|B7b9|Em7|A7|Am7 F#dim7|Fm11 Bb7'),
 ('C','Eb|Eb/G|Abadd2|Bb11|Cm7 F7|Bb7sus4 Bb7/D|Ebsus4|Eb')],note='Lige ottendedele, two-beat ved 60 som i Helles’ aftaler. Modulationen i B og tilbagevendingen til E♭ er bevaret.',config={'style':'jazzballad','feel':'two','swing':False})
add('The Guaracha','Cm',120,'Guaracha / cha-cha-cha','guaracha-leadsheet.pdf',[
 ('Vers','Cm|Cm|Cm|G7|G7|G7|G7|Cm|Cm|Cm|Cm|Fm|Fm|G7|G7|Cm'),
 ('Refræn','Cm|G7|G7|Cm|Cm|G7|G7|Cm')],note='Efter Guaracha(1).pdf. Tempo er ikke angivet; 120 er et valgt øvetempo. Latinakkompagnement med percussion.',config={'style':'custom','bass':'alternate','chords':'offbeat','drums':'percussion','bassInstrument':32,'chordInstrument':0})
add('Oy como va','Am',125,'Cha-cha-cha / Latin','',[
 ('Intro / tema', 'Am7|D7|Am7|D7|Am7|D7|Am7|D7'),
 ('Sang','Am7|D7|Am7|D7|Am7|D7|Am7|D7'),
 ('Solo-vamp','Am7|D7|Am7|D7|Am7|D7|Am7|D7')],note='To-takters vamp efter Tito Puentes indspilning på Chordify. 24-takters øveform; Helles’ koncertform og tempo er endnu ikke dokumenteret.',config={'style':'custom','bass':'alternate','chords':'offbeat','drums':'percussion','bassInstrument':32,'chordInstrument':0})
charts[-1]['url']='https://chordify.net/chords/tito-puente-songs/oye-como-va-3-chords'
add('Sakta vi gå genom stan','Bb',108,'Swing','sakta-vi-ga-genom-stan-leadsheet.pdf',[
 ('A1','Bbmaj7 F9#5|Bbmaj7 F9#5|Bbmaj7 Eb7|Dm7b5 G7b9|Cm7 G7/B|Cm7 Am7b5|Ab7 G7 Gb7b5 F7|Bbmaj7 F9#5'),
 ('A2','Bbmaj7 F9#5|Bbmaj7 F9#5|Bbmaj7 Eb7|Dm7b5 G7b9|Cm7 G7/B|Cm7 Am7b5|Ab7 G7 Gb7b5 F7|Bbmaj7 A7b9'),
 ('B','Dm7 Dmmaj7/C#|Dm7/C Bm7b5|Bbmaj7|Em7b5 A7b9|Dm7 Dmmaj7/C#|Dm7/C Bm7b5|Gm7 C7|Cm7 F7b9'),
 ('A3','Bbmaj7 F9#5|Bbmaj7 F9#5|Bbmaj7 Eb7|Dm7b5 G7b9|Cm7 G7/B|Cm7 F7|Cm7 F7|Bb6:2 Cm7:1 F7:1')],note='Første 32-takters harmoniske grundform efter PDF (A gentages med to slutninger). Senere tekstvers og slutforlængelser står i original-PDF’en; solorækkefølge følger spilleaftalerne.')
add('Visan från Utanmyra','Am',103,'Ballad','',[
 ('A','Am|E|Am|E|Am|D|Am G|C|Em|E|Am|Em|C|E|Am|G'),
 ('B','F|E|Am|E|F|C|C|G|Am|Am|Am|E|Am|Am|Am|Am')],note='Forenklet harmonisk øveform efter Chordifys analyse af Jan Johansson/Georg Riedel. Ikke en transskription af alle klavervariationer i PDF’en; Helles’ toneart og tempo afventer bekræftelse.')
charts[-1]['url']='https://chordify.net/chords/jan-johansson-songs/visa-fran-utanmyra-chords'

def abc_chart(chart):
    meter=chart['meter']; n,d=map(int,meter.split('/')); beats=Fraction(n*4,d)
    out=[f"X:1\nT:{chart['title']}\nR:{chart['style']}\nM:{meter}\nL:1/4\nQ:1/4={chart['tempo']}\nK:{chart['key']}\n%%barsperstaff 4\n"]
    count=0
    for name,bars in chart['sections']:
        out.append('P:'+name+'\n')
        for bar in bars.split('|'):
            change=re.match(r'\{([^}]+)\}',bar)
            if change:
                meter=change[1];n,d=map(int,meter.split('/'));beats=Fraction(n*4,d);out.append('[M:'+meter+']');bar=bar[change.end():]
            tokens=bar.strip().split(); lengths=[]
            explicit=all(':' in t for t in tokens)
            assert explicit or not any(':' in t for t in tokens),bar
            for t in tokens:
                chord,sep,duration=t.partition(':'); length=Fraction(duration) if sep else (Fraction([2,1,1][len(lengths)]) if beats==4 and len(tokens)==3 else Fraction([0.5,0.5,1,1,1][len(lengths)]) if beats==4 and len(tokens)==5 else beats/len(tokens))
                lengths.append(length);out.append('"'+chord+'"z'+(str(length) if length!=1 else '')+' ')
            assert sum(lengths)==beats,(chart['title'],name,bar,lengths,beats)
            out.append(' | ');count+=1
            if count%4==0:out.append('\n')
        out.append('||\n')
    out.append('|]\n')
    return ''.join(out),count

def build():
    rows=[]
    for chart in charts:
        abc,bars=abc_chart(chart); title=chart['title']+' · ABC-akkordark'
        note=chart['note'] or 'Becifringer efter Helles’ originale PDF. Én harmonisk grundform til øvning.'
        config={'enabled':True,'style':'auto'};config.update(chart['config'] or {})
        source='pdf/'+chart['pdf'] if chart['pdf'] else chart.get('url','')
        rows.append({'title':title,'caption':chart['title'],'type':'text/vnd.tiddlywiki','text':'<$huwiki-repertoire-piece tiddler=<<currentTiddler>>/>\n\n'+note,
          'music-template':'off','repertoire-work-title':chart['title'],'repertoire-sheet-format':'abc','repertoire-source-role':'chord-stabs','repertoire-abc-label':'Akkordark (ABC)',
          'abc-source':abc,'abc-key':chart['key'],'abc-genre':chart['style'],'abc-view':'chords','abc-bars-per-line':'4','abc-accompaniment':json.dumps(config,ensure_ascii=False),
          'helles-source-file':source,'helles-source-note':note,'helles-source-url':chart.get('url',''),'helles-written-bars':str(bars),
          'helles-verification':'PDF-transskription' if chart['pdf'] else 'Indspilningsbaseret øveform; afventer Helles-arrangement'})
        canonical={'title':chart['title'],'repertoire-chord-stabs-source':title,'repertoire-abc-playback-source':title}
        if chart['title'] in ('Har du visor, min vän','The Guaracha','Oy como va','Visan från Utanmyra'):
            canonical.update({'repertoire-key':chart['key'],'repertoire-tempo':'1/4='+str(chart['tempo']),'helles-source-note':note})
        rows.append(canonical)
    (DATA/'chordsheet-additions.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    (DATA/'chordsheet-transcriptions.json').write_text(json.dumps(charts,ensure_ascii=False,indent=2)+'\n')
    print('Built',len(charts),'ABC chord charts')
if __name__=='__main__':build()
