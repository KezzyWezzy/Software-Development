const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, PageBreak,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, LevelFormat,
  convertInchesToTwip,
} = require('docx');
const fs = require('fs');

const PAGE_W = 12240, PAGE_H = 15840;
const MARGIN = 1296;                 // 0.9"
const CW = PAGE_W - 2 * MARGIN;      // 9648 content width

// ---------- helpers ----------
const NONE = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };

function run(t, o = {}) { return new TextRun({ text: t, ...o }); }
// Fill-in blank: yellow background via run shading (w:shd). Do NOT use `highlight:` —
// docx-js pairs it with a <w:highlightCs> element that is not valid per the OOXML schema.
function fill(t) {
  return new TextRun({
    text: t, bold: true, color: '6B4E00',
    shading: { type: ShadingType.CLEAR, fill: 'FFF3C4' },
  });
}
function b(t) { return new TextRun({ text: t, bold: true }); }
function i(t) { return new TextRun({ text: t, italics: true }); }

function p(children, o = {}) {
  const kids = typeof children === 'string' ? [run(children)] : children;
  return new Paragraph({
    children: kids,
    alignment: o.align || AlignmentType.JUSTIFIED,
    spacing: { after: o.after === undefined ? 140 : o.after, line: 276 },
    ...o.rest,
  });
}
function pl(children, o = {}) { return p(children, { align: AlignmentType.LEFT, ...o }); }
function pc(children, o = {}) { return p(children, { align: AlignmentType.CENTER, ...o }); }

function title(t) {
  return new Paragraph({
    children: [new TextRun({ text: t, bold: true, size: 30 })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 120 },
  });
}
function h2(t) { return new Paragraph({ text: t, heading: HeadingLevel.HEADING_2 }); }
function h3(t) { return new Paragraph({ text: t, heading: HeadingLevel.HEADING_3 }); }

function li(children, ref, level = 0) {
  const kids = typeof children === 'string' ? [run(children)] : children;
  return new Paragraph({
    children: kids,
    numbering: { reference: ref, level },
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 110, line: 276 },
  });
}
function bul(children) {
  const kids = typeof children === 'string' ? [run(children)] : children;
  return new Paragraph({
    children: kids,
    bullet: { level: 0 },
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 110, line: 276 },
  });
}

function pageBreak() { return new Paragraph({ children: [new PageBreak()] }); }

// bordered callout box (single-cell table)
function box(paras, shaded = true) {
  return new Table({
    columnWidths: [CW],
    width: { size: CW, type: WidthType.DXA },
    rows: [new TableRow({
      children: [new TableCell({
        width: { size: CW, type: WidthType.DXA },
        margins: { top: 160, bottom: 160, left: 200, right: 200 },
        shading: shaded ? { type: ShadingType.CLEAR, fill: 'F2F4F6' } : undefined,
        children: paras,
      })],
    })],
  });
}

// two-column label/value table
function kvTable(rows, labelW = 3100) {
  const valW = CW - labelW;
  return new Table({
    columnWidths: [labelW, valW],
    width: { size: CW, type: WidthType.DXA },
    rows: rows.map(([k, v]) => new TableRow({
      children: [
        new TableCell({
          width: { size: labelW, type: WidthType.DXA },
          shading: { type: ShadingType.CLEAR, fill: 'EEF0F3' },
          margins: { top: 60, bottom: 60, left: 120, right: 120 },
          children: [pl([b(k)], { after: 0 })],
        }),
        new TableCell({
          width: { size: valW, type: WidthType.DXA },
          margins: { top: 60, bottom: 60, left: 120, right: 120 },
          children: [pl(typeof v === 'string' ? [run(v)] : v, { after: 0 })],
        }),
      ],
    })),
  });
}

function gridTable(widths, header, rows) {
  const mk = (txt, bold, shade) => new TableCell({
    width: { size: 0, type: WidthType.DXA },
    shading: shade ? { type: ShadingType.CLEAR, fill: 'EEF0F3' } : undefined,
    margins: { top: 60, bottom: 60, left: 120, right: 120 },
    children: [pl(typeof txt === 'string' ? [run(txt, { bold })] : txt, { after: 0 })],
  });
  const fix = (cells, w) => cells.map((c, idx) => {
    c.options = c.options || {};
    return c;
  });
  return new Table({
    columnWidths: widths,
    width: { size: CW, type: WidthType.DXA },
    rows: [
      new TableRow({
        tableHeader: true,
        children: header.map((t, idx) => new TableCell({
          width: { size: widths[idx], type: WidthType.DXA },
          shading: { type: ShadingType.CLEAR, fill: 'EEF0F3' },
          margins: { top: 60, bottom: 60, left: 120, right: 120 },
          children: [pl([b(t)], { after: 0 })],
        })),
      }),
      ...rows.map(r => new TableRow({
        children: r.map((t, idx) => new TableCell({
          width: { size: widths[idx], type: WidthType.DXA },
          margins: { top: 60, bottom: 60, left: 120, right: 120 },
          children: [pl(typeof t === 'string' ? [run(t)] : t, { after: 0 })],
        })),
      })),
    ],
  });
}

const SIGLINE = '______________________________________';
const spacer = (n = 200) => new Paragraph({ text: '', spacing: { after: n } });

// ---------- numbering ----------
function decConfig(ref) {
  return {
    reference: ref,
    levels: [{
      level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.START,
      style: { paragraph: { indent: { left: 720, hanging: 360 } } },
    }],
  };
}
function alphaConfig(ref) {
  return {
    reference: ref,
    levels: [{
      level: 0, format: LevelFormat.LOWER_LETTER, text: '(%1)', alignment: AlignmentType.START,
      style: { paragraph: { indent: { left: 720, hanging: 400 } } },
    }],
  };
}

// ============================================================
//  CONTENT
// ============================================================
const kids = [];
const A = (...x) => kids.push(...x);

// ---------- COVER ----------
A(
  title('Evidence Preservation and Video Production Packet'),
  pc([run('Miami International Airport — escalator fall of July 27, 2026')], { after: 0 }),
  pc([run('Prepared for Keith Vallone')], { after: 240 }),

  box([p([
    b('This is a drafting aid, not legal advice.'),
    run(' It was not prepared by a lawyer and no attorney–client relationship exists. Deadlines in Florida tort and public-records practice are unforgiving, and the documents below make binding legal commitments. Have a Florida-licensed attorney review this packet before you sign or send anything — most personal-injury attorneys will review a preservation letter at no charge.'),
  ], { after: 0 })]),
  spacer(200),

  h2('What this packet does'),
  p('Your objective is production of the video, not litigation. The problem is that a request with no consequence attached gets filed and forgotten, while surveillance video overwrites itself on a fixed cycle. This packet therefore attacks the problem on four independent tracks at once, so that no single refusal ends the matter:'),
  li([b('A litigation hold / spoliation notice.'), run(' This is the most important page in the packet and it works whether or not anyone cooperates. Once the County is on written notice that litigation is reasonably anticipated, its duty to preserve the footage attaches. If it lets the video overwrite after receiving this letter, Florida courts can strike defenses and instruct a jury to presume the destroyed video was unfavorable to the County. That converts "we deleted it" from an escape into a liability.')], 'n1'),
  li([b('A Chapter 119 public records request.'), run(' Miami-Dade County is a political subdivision, so its records are presumptively public and must be produced promptly.')], 'n1'),
  li([b('A conditional release (Exhibit A).'), run(' The carrot. A full release of claims that has no force whatsoever unless they deliver usable video within the deadline.')], 'n1'),
  li([b('A stated fallback.'), run(' Explicit notice that if the deadline passes, you serve the §768.28 pre-suit notice and proceed. The offer is only credible if the alternative is.')], 'n1'),

  h2('Documents included'),
  gridTable([620, 5400, 3628],
    ['#', 'Document', 'Send to'],
    [
      ['1', 'Demand letter — preservation, records request, and conditional offer', 'Miami-Dade Aviation Department (Risk Management + Records Custodian) and County Attorney'],
      ['2', 'Exhibit A — Conditional Release and Covenant Not to Sue', [run('Enclose with Document 1. '), b('Do not sign until video is delivered.')]],
      ['3', 'Companion letter — American Airlines', 'AA Customer Relations / Legal'],
      ['4', 'FOIA request — U.S. Customs and Border Protection', [b('Send this. '), run('The timeline places the fall inside or adjacent to the federal inspection area — see below')]],
      ['5', 'Optional — §768.28 pre-suit notice of claim', 'Hold in reserve. Send only if the deadline passes.'],
    ]),
  spacer(160),

  h2('The time window, and how it was derived'),
  p('You recall falling about twenty minutes after getting off the Cozumel flight. Working forward from the published schedule for AA 4072:'),
  kvTable([
    ['Scheduled departure, Cozumel', '3:20 p.m. Cozumel time (UTC−5, no daylight saving)'],
    ['Same moment in Miami time', '4:20 p.m. EDT'],
    ['Scheduled block time', '1 hour 46 minutes'],
    ['Scheduled gate arrival, MIA', '6:06 p.m. EDT — North Terminal (Concourse D)'],
    ['Deplaning begins', 'roughly 6:10–6:15 p.m. EDT'],
    ['Fall, ~20 min after deplaning', [b('approximately 6:30–6:45 p.m. EDT')]],
    ['Preservation window demanded', '2:30 p.m. – 10:30 p.m. EDT (four hours either side)'],
  ], 4000),
  spacer(200),
  box([p([
    b('This is a schedule-derived estimate, not a confirmed arrival time.'),
    run(' It was not possible to reach flight-history databases to pull the actual gate arrival for July 27, 2026 — those sites are blocked from the environment this was drafted in. Delays are routine, and if AA 4072 landed an hour late then every figure above shifts by an hour. Confirm the actual time before you send anything. The letters deliberately demand a wide preservation window precisely so that an error of an hour or two does not cost you the footage.'),
  ], { after: 0 })]),
  spacer(200),
  h3('How to pin down the actual time'),
  bul([b('The American app or aa.com under "Your trips"'), run(' — the receipt for a flown segment usually shows the actual arrival time.')]),
  bul([b('Your phone.'), run(' Photos, texts, and calls from that afternoon bracket the fall from both sides. If you have Google Maps Timeline (Android) or Significant Locations (iPhone) enabled, it will place you inside the airport minute by minute — usually the most precise record anyone has.')]),
  bul([b('Any card transaction'), run(' at the airport that evening.')]),
  bul([b('Your CBP arrival record'), run(' at i94.cbp.dhs.gov, which confirms the date and port of entry.')]),
  bul([b('Document 3 asks American for it in writing'), run(' — the actual gate-in time and the gate assignments for both segments.')]),

  h2('Why CBP now matters more than the airport'),
  p([run('Twenty minutes after stepping off an international flight, you were in all likelihood '), i('still inside the federal inspection area'), run(' — the sterile arrivals corridor, the walk toward passport control, the immigration queue, or the descent toward customs and baggage claim. American’s Cozumel service arrives in the North Terminal, and arriving international passengers are held within that controlled path until they clear CBP and are released into the public side of the airport.')]),
  p([run('That reorders the priorities from the original draft. Cameras in that zone are federal, and Miami-Dade County cannot produce that footage however cooperative it is — it does not own it. '), b('Send Document 4. It is no longer a contingency.'), run(' Send Document 1 as well: the County may hold overlapping views, the exact boundary is not something anyone can reconstruct reliably from memory, and the preservation demand costs nothing to make.')]),
  p('The one thing that would flip this back toward the County is if you had already cleared customs and re-entered the public terminal before you fell. Twenty minutes is fast for a full clearance, but it is not impossible with Global Entry or Mobile Passport, no checked bags, and short queues. If that describes your arrival, say so — Document 1 becomes the primary track and Document 4 the backup. If you are unsure, send both and let the two custodians sort it out between them.'),
  p('Photographing or recording inside the federal inspection area is prohibited, which is exactly why the government’s own footage may be the only record of what happened to you that exists anywhere.'),

  h2('Before you send — fill in every highlighted blank'),
  bul([b('Time of the fall.'), run(' Pre-filled as approximately 6:30–6:45 p.m. Eastern, derived from the scheduled arrival of AA 4072 as set out above. '), b('Verify it'), run(' against the actual arrival time and correct it if the flight was delayed. Keep it stated as a window, never a single minute.')]),
  bul([b('Location, as precisely as you can manage.'), run(' Concourse letter, gate numbers on either side, the level you were traveling between, and any fixed landmark you can name — a specific retailer, a restroom, a baggage carousel number. "An escalator at MIA" is a request they can honestly fail to fill; "the down escalator between Concourse D gates 30 and 32" is not.')]),
  bul([b('Direction of travel'), run(' (up or down, and toward what).')]),
  bul([b('Witnesses and responders.'), run(' Any name, badge, uniform, or employer you remember.')]),
  bul([b('Whether an incident report was made'), run(', and by whom.')]),
  bul([b('Injuries and treatment.'), run(' If you saw any medical provider, say so and keep the records.')]),
  p('If you genuinely cannot recall a detail, write "unknown" rather than guessing. An inaccurate statement in a preservation letter is worth far less than an incomplete one, and it will be quoted back to you.'),

  h2('How to send'),
  p([run('Certified mail, return receipt requested, '), i('and'), run(' email to each recipient the same day. Keep the green card, the delivery confirmation, and the sent email. Proof of the date they received notice is what makes the preservation duty enforceable, so treat the receipts as part of the evidence file. Calendar the response deadline the day you mail it.')]),

  h2('Do this today, regardless of the letters'),
  bul('Write out everything you remember about the fall now, dated, before it fades.'),
  bul('Preserve your own materials — boarding passes, the AA app screenshots, photos, texts or calls you made that day, the clothing and shoes you were wearing, and any medical paperwork.'),
  bul('If you have not been evaluated by a doctor, consider it. Delayed documentation of an injury is the single most common weakness in these claims.'),
  bul('Do not post about the incident publicly and do not give a recorded statement to any insurer or claims adjuster before you speak with a lawyer.'),
  spacer(120),

  box([p([
    b('On timing.'),
    run(' Airport surveillance systems commonly overwrite on a cycle measured in days or weeks, not months. Your fall was on July 27, 2026. Whatever else you do with this packet, get the preservation letter into the County’s hands immediately — an unsigned, imperfect letter delivered this week is worth more than a polished one delivered next month.'),
  ], { after: 0 })]),
  spacer(160),
  p([run('Nothing in this packet is legal advice. Statutory citations are provided for your attorney’s convenience and should be independently verified against current Florida law before use.', { size: 19, color: '4A4F57' })]),
  pageBreak(),
);

// ---------- DOCUMENT 1 ----------
A(
  pl([b('Keith Vallone')], { after: 0 }),
  pl([fill('[Street address]')], { after: 0 }),
  pl([fill('[City, State ZIP]')], { after: 0 }),
  pl([fill('[Phone]'), run('  |  '), fill('[Email]')], { after: 240 }),
  pl([fill('[Date]')], { after: 200 }),
  pl([b('VIA CERTIFIED MAIL, RETURN RECEIPT REQUESTED, AND ELECTRONIC MAIL')], { after: 200 }),
  pl('Miami-Dade Aviation Department', { after: 0 }),
  pl('Attn: Risk Management / Claims, and Custodian of Public Records', { after: 0 }),
  pl('P.O. Box 592075', { after: 0 }),
  pl('Miami, Florida 33159', { after: 180 }),
  pl([i('cc: '), run('Miami-Dade County Attorney’s Office')], { after: 0 }),
  pl('111 N.W. First Street, Suite 2810, Miami, Florida 33128', { after: 220 }),

  pl([b('RE:  NOTICE OF EVIDENCE PRESERVATION OBLIGATION; PUBLIC RECORDS REQUEST; AND CONDITIONAL OFFER OF FULL RELEASE IN EXCHANGE FOR TIMELY PRODUCTION OF SURVEILLANCE VIDEO')], { after: 200 }),

  kvTable([
    ['Claimant', 'Keith Vallone'],
    ['Date of incident', 'July 27, 2026'],
    ['Approximate time', [run('Approximately '), fill('6:30 p.m. – 6:45 p.m. Eastern time — verify against actual arrival')]],
    ['Location', [run('Miami International Airport — '), fill('[concourse, level, nearest gates or landmark]')]],
    ['Nature of incident', 'Fall on an escalator'],
    ['Itinerary', 'American Airlines Flight 4072, Cozumel (CZM) to Miami (MIA), continuing MIA to New Orleans (MSY), July 27, 2026'],
    ['Ticket number', '0012363031275'],
    ['Confirmation code', 'OYRTCS'],
  ]),
  spacer(200),

  pl('Dear Sir or Madam:'),
  p([run('I write regarding a fall I sustained on an escalator at Miami International Airport on July 27, 2026, while connecting between the flights identified above. I am writing to you directly, without counsel and without a lawsuit on file, because what I want from the County is narrow and specific: '), b('the surveillance video of the incident.'), run(' This letter (1) places the County on formal notice of its obligation to preserve evidence, (2) requests records under Chapter 119, Florida Statutes, and (3) offers the County a complete and final release of all claims arising from this incident in exchange for prompt production of that video.')]),

  h2('I. The Incident'),
  p([
    run('American Airlines Flight 4072 from Cozumel was scheduled to arrive at Miami International Airport at 6:06 p.m. Eastern time on July 27, 2026. I deplaned shortly after the aircraft reached the gate and fell approximately twenty minutes later, which places the incident at roughly '),
    fill('6:30 p.m. to 6:45 p.m.'), run(' '),
    b('The County can fix this time precisely from its own gate records, flight information system, and camera timestamps for that arrival, and I ask that it do so rather than treat my estimate as the limit of the search.'),
    run(' If the flight arrived late, the incident time shifts correspondingly, which is why the preservation window demanded below is deliberately broad.'),
  ]),
  p([
    run('On July 27, 2026, at approximately '), fill('6:35 p.m.'), run(', I was traveling '),
    fill('[direction — e.g., downward]'), run(' on the escalator located at '),
    fill('[describe location as precisely as possible]'), run(' when I fell. '),
    fill('[Add a brief, factual description of the fall and of any condition you observed — for example, an abrupt stop or jolt, an uneven or damaged step, a missing or non-moving handrail, a wet or slick step surface, inadequate lighting, or an absent warning sign. State only what you actually observed. If you do not know what caused the fall, say so plainly.]'),
  ]),
  p([fill('[If applicable: I was assisted by / observed by the following persons — names, descriptions, uniforms, badge numbers, or employers. An incident report was completed by ____ .]')]),
  p([fill('[If applicable: I sustained the following injuries and received medical evaluation or treatment at ____ on ____ .]')]),
  p('I do not presently know what caused my fall, and I am not asserting in this letter that the County was negligent. That is precisely the point. The surveillance video is the only complete and objective record of what occurred, and it is in the County’s exclusive possession. Whether it exonerates the County or implicates it, it should be produced.'),

  h2('II. Notice of Preservation Obligation — Litigation Hold'),
  p([b('Litigation arising from this incident is reasonably anticipated. This letter constitutes formal written notice of that fact.'), run(' The County’s common-law obligation to preserve relevant evidence attaches upon receipt of this letter, if it has not already attached. You are directed to suspend immediately any automatic deletion, overwrite, recycling, purge, or retention-cycle process that would destroy or degrade any of the following, and to issue a written litigation hold to every custodian, department, contractor, and vendor in possession of it:')]),
  li([b('All surveillance and CCTV video'), run(' — recorded, archived, exported, or live-buffered — depicting the escalator identified above, its landings, and the approaches to it, from '), b('four (4) hours before'), run(' through '), b('four (4) hours after'), run(' the incident, and in any event covering no narrower a period than '), b('2:30 p.m. to 10:30 p.m. Eastern time on July 27, 2026'), run('. This period is stated in the alternative because my estimate of the time is derived from the scheduled arrival of Flight 4072 and the County is better positioned than I am to determine the actual arrival time; the video is not to be withheld or the search narrowed on the ground that my estimate was imprecise. This includes every camera with any view of the location, not solely the camera with the best view, and includes footage from cameras owned or operated by tenants, concessionaires, or contractors to the extent the County has possession, custody, or control of it.')], 'n2'),
  li([b('All video of the same escalator'), run(' for the seven (7) days preceding the incident, which bears directly on notice of any recurring or dangerous condition.')], 'n2'),
  li([b('All native metadata'), run(' associated with the foregoing — camera identifiers, positions and fields of view, frame rates, resolution settings, time-synchronization data, and audit or export logs showing every person who viewed, copied, exported, or deleted the footage.')], 'n2'),
  li([b('All incident, accident, injury, and first-responder records'), run(' relating to the incident, including any report by airport operations, airport police, Miami-Dade Fire Rescue, emergency medical services, or any airline or contractor employee.')], 'n2'),
  li([b('All maintenance, inspection, service, repair, testing, and certification records'), run(' for the escalator for the twenty-four (24) months preceding the incident, including work orders, service call logs, callback records, fault and alarm logs, elevator/escalator inspection certificates, and all records of any emergency stop, malfunction, or shutdown.')], 'n2'),
  li([b('All records of prior incidents, falls, injuries, complaints, or claims'), run(' involving this escalator or any escalator at the airport for the sixty (60) months preceding the incident.')], 'n2'),
  li([b('All contracts, service agreements, and correspondence'), run(' with any vendor responsible for the maintenance, inspection, or repair of this escalator.')], 'n2'),
  li([b('All internal communications'), run(' — email, text messages, radio logs, dispatch records, ticketing systems, and messaging platforms — concerning the incident or the condition of the escalator.')], 'n2'),
  li([b('The physical escalator itself'), run(' in its post-incident condition. Do not alter, repair, modify, or replace any component without first preserving it and providing me notice and a reasonable opportunity to inspect. If safety requires immediate repair, photograph and document the condition thoroughly beforehand and retain every removed component.')], 'n2'),
  spacer(120),

  box([p([
    b('Consequences of destruction.'),
    run(' Under Florida law, a party that destroys or fails to preserve evidence after its duty to preserve has attached may be sanctioned, including by the striking of pleadings and defenses and by a jury instruction permitting or requiring the presumption that the destroyed evidence was unfavorable to that party. If this video is permitted to overwrite '),
    i('after the County’s receipt of this letter'),
    run(', that destruction will not be treated as routine records management. I will seek every available remedy for spoliation, and the County will be litigating the destruction of the evidence rather than the merits of the incident.'),
  ], { after: 0 })]),
  spacer(200),

  p([run('Please confirm in writing within '), b('five (5) business days'), run(' of receipt that (a) a litigation hold has issued, (b) the video described above has been located and exported to preservation media outside any automatic overwrite cycle, and (c) the retention period and overwrite interval of the surveillance system in question. If the footage has '), i('already'), run(' been overwritten or is otherwise unavailable, say so immediately and in writing, and identify the date of destruction, the retention policy under which it occurred, and every person who viewed or exported it before it was lost.')]),

  h2('III. Public Records Request — Chapter 119, Florida Statutes'),
  p('Separately and independently of the foregoing, I request under Article I, Section 24 of the Florida Constitution and Chapter 119, Florida Statutes, copies of the records described in Paragraphs 1 and 3 through 8 of Section II above. I request the video in its native or an unaltered digital format, delivered by secure download link, cloud transfer, or on physical media, at my expense.'),
  p('Please note the following, and treat this paragraph as the written request contemplated by the statute:'),
  bul([run('Please acknowledge this request promptly and provide a good-faith estimate of the time required to respond and of any statutorily authorized cost. '), b('I agree in advance to pay reasonable duplication and extensive-use charges up to $'), fill('[e.g., 250]'), b(' without further approval'), run(', so that cost is not a reason for delay. If the anticipated charge exceeds that amount, contact me before incurring it and I will respond the same day.')]),
  bul('If any portion of a requested record is claimed to be exempt or confidential, produce all non-exempt portions and redact only the exempt material, and state in writing the specific statutory citation for each exemption asserted and the basis for its application to each withheld record, as the public records law requires.'),
  bul('To the extent the County asserts a security-related exemption, I note that I am not seeking camera placements, system schematics, coverage maps, or any information about the design or capabilities of the airport’s security infrastructure, and I consent to the redaction, obscuring, or cropping of any such information. I seek only the recorded images of a fall by a member of the public in a publicly accessible passenger circulation area. If the County’s position is that this footage cannot be produced under Chapter 119 in any form, state that position in writing with citation, and produce it instead under the voluntary framework in Section IV, which does not depend on the public records law at all.'),

  h2('IV. Conditional Offer — Full Release in Exchange for the Video'),
  p([run('I want to resolve this simply, and I am prepared to give up a great deal to do so. '), b('If the County produces to me, on or before '), fill('[date — recommend 21 calendar days from the date of this letter]'), b(', a complete, unedited, and viewable copy of the surveillance video described in Paragraph II(1), I will execute and deliver the Conditional Release and Covenant Not to Sue attached as Exhibit A, fully and finally releasing Miami-Dade County, the Miami-Dade Aviation Department, and their officers, employees, and agents from every claim arising out of this incident.')]),
  p('The terms of that offer are as follows, and Exhibit A is drafted to match them exactly:'),
  bul([run('The release is '), b('conditional and self-executing'), run('. It becomes effective automatically upon timely delivery of conforming video, and it is '), b('void and of no effect'), run(' if the video is not delivered by the deadline, is materially incomplete, is unviewable, or does not depict the incident. Nothing is released unless and until the County performs.')]),
  bul([run('The release is '), b('full and final'), run(' as to the County and covers all claims, known and unknown, arising from this incident.')]),
  bul([run('It requires '), b('no payment of any kind'), run(' from the County. I am not asking for money. I am asking for a video file.')]),
  bul([run('It is '), b('not an admission'), run(' by the County of liability, fault, negligence, or of the existence of any defect, and Exhibit A says so expressly.')]),
  bul([run('This offer, and any communication about it, is made in the course of compromise negotiations and is '), b('not an admission by me'), run(' that any claim is or is not meritorious.')]),
  p('I recognize that the County may view the release of an unlitigated claim as a favorable outcome that costs it nothing but the effort of an export. That is the intended bargain. I am trading away every remedy I may have for the ability to see what happened to me.'),

  h2('V. If the Deadline Passes'),
  p('I would rather not go further than this letter, but the offer in Section IV is meaningful only if the alternative is real, so I will state the alternative plainly. If conforming video is not delivered by the deadline above, and no written agreement extending it has been reached, then the offer in Section IV expires automatically and without further notice, Exhibit A becomes void, and I will:'),
  li('Serve formal pre-suit notice of claim on the County and on the Florida Department of Financial Services pursuant to §768.28(6), Florida Statutes, and begin the statutory investigation period;', 'n3'),
  li('Retain counsel and pursue the video through compulsory discovery, where production is not discretionary and where the County’s retention practices, its handling of this letter, and the identity of everyone who viewed the footage all become discoverable;', 'n3'),
  li([run('Pursue every available remedy under §119.12, Florida Statutes, for any unlawful refusal of the public records request in Section III, including attorney’s fees and costs. '), b('This paragraph is intended to serve as the written notice to the custodian of public records required by §119.12(1)(b) before the filing of such an action'), run(', and no such action will be filed sooner than five (5) business days after your receipt of this letter; and')], 'n3'),
  li('Seek sanctions and an adverse-inference instruction for spoliation if the video is destroyed after your receipt of this letter.', 'n3'),
  p('None of that serves the County and none of it serves me. All of it is avoided by sending a video file.'),

  h2('VI. Response'),
  p('Please direct all correspondence to me at the address above. I am willing to sign a reasonable confidentiality agreement limiting my use of the footage, to accept redaction of uninvolved persons’ faces, and to travel to a County facility to view the video in person if production of a copy is genuinely not possible — though I ask that you not treat in-person viewing as a substitute for production without first explaining in writing why a copy cannot be provided.'),
  p('I have tried to make this as easy as possible to say yes to. Please do not let the retention cycle decide this for both of us.'),
  spacer(240),
  pl('Respectfully,', { after: 400 }),
  pl(SIGLINE, { after: 0 }),
  pl([b('Keith Vallone')], { after: 240 }),
  pl([b('Enclosures: '), run('Exhibit A — Conditional Release and Covenant Not to Sue (unexecuted); copy of ticket and itinerary documentation '), fill('[list any other enclosures]')]),
  pageBreak(),
);

// ---------- DOCUMENT 2 — EXHIBIT A ----------
A(
  title('EXHIBIT A'),
  title('CONDITIONAL RELEASE AND COVENANT NOT TO SUE'),
  spacer(160),
  p([run('This Conditional Release and Covenant Not to Sue (this "Release") is made by '), b('Keith Vallone'), run(' ("Releasor") in favor of '), b('Miami-Dade County, Florida'), run(', acting by and through the Miami-Dade Aviation Department, and its past and present officers, employees, agents, departments, and elected officials (collectively, "Releasee").')]),

  h2('Recitals'),
  p([b('A.'), run(' On July 27, 2026, Releasor fell on an escalator located at Miami International Airport at or near '), fill('[location]'), run(' (the "Incident").')]),
  p([b('B.'), run(' Releasee is in possession of surveillance video recorded at the time and place of the Incident (the "Video").')]),
  p([b('C.'), run(' Releasor seeks production of the Video and does not seek monetary compensation from Releasee. Releasor is willing to release all claims arising from the Incident in exchange solely for timely production of the Video, and on no other consideration.')]),
  p([b('D.'), run(' Releasee denies any liability, fault, or wrongdoing in connection with the Incident.')]),

  h2('Terms'),
  h3('1. Condition Precedent'),
  p([run('This Release is expressly conditioned upon, and shall become effective only upon, the occurrence of the Triggering Event defined in Section 2. '), b('Until the Triggering Event occurs, this Release is of no force or effect whatsoever, releases nothing, and confers no right, benefit, or defense upon Releasee.'), run(' Execution and delivery of this instrument by Releasor does not itself release any claim.')]),

  h3('2. Triggering Event'),
  p([run('The "Triggering Event" occurs when all of the following have been satisfied on or before '), fill('[deadline date]'), run(' (the "Deadline"):')]),
  li('Releasee delivers to Releasor a digital copy of the Video covering, at minimum, the period beginning thirty (30) minutes before and ending thirty (30) minutes after the Incident;', 'alpha1'),
  li('The delivered footage is complete and continuous for that period, is not edited, truncated, or materially degraded, and is playable using commonly available video software or with a player or codec supplied by Releasee;', 'alpha1'),
  li('The delivered footage visually depicts the Incident, including Releasor’s fall and the moments immediately preceding and following it; and', 'alpha1'),
  li('Releasee delivers a written statement, signed by an authorized representative, identifying the camera or cameras from which the footage was taken, the date and time range covered, confirming that the footage has not been altered other than by any redaction disclosed in the statement, and describing any redaction applied.', 'alpha1'),
  p('Redaction limited to obscuring the faces of uninvolved members of the public shall not, by itself, cause the footage to be deemed non-conforming, provided such redaction does not obscure Releasor, the escalator, or the Incident.'),

  h3('3. Release'),
  p('Effective automatically and without further act upon the occurrence of the Triggering Event, Releasor fully, finally, and forever releases, acquits, and discharges Releasee from any and all claims, demands, causes of action, damages, costs, expenses, and liabilities of every kind and nature, whether known or unknown, suspected or unsuspected, foreseen or unforeseen, in law or in equity, arising out of or in any way related to the Incident, including without limitation all claims for personal injury, bodily injury, pain and suffering, mental anguish, medical and related expenses, lost wages and lost earning capacity, disability, disfigurement, loss of enjoyment of life, and property damage.'),

  h3('4. Covenant Not to Sue'),
  p('Effective upon the occurrence of the Triggering Event, Releasor covenants not to commence, prosecute, maintain, or voluntarily assist in any action, suit, claim, administrative proceeding, or arbitration against Releasee arising out of the Incident. This covenant does not prohibit Releasor from responding truthfully to lawful process or from cooperating with any governmental investigation.'),

  h3('5. Failure of Condition; Automatic Nullity'),
  p([run('If the Triggering Event has not occurred by the Deadline, this Release shall be '), b('automatically void '), new TextRun({ text: 'ab initio', bold: true, italics: true }), b(', without any notice, declaration, or further act by Releasor'), run(', and shall be of no force or effect for any purpose. In that event, Releasor retains in full every claim, right, and remedy Releasor may have arising out of the Incident, without limitation or waiver, exactly as if this instrument had never been executed. No delay by Releasor in asserting the nullity of this Release, and no partial or late performance accepted by Releasor, shall constitute a waiver of this Section or a ratification of this Release. The Deadline may be extended only by a writing signed by Releasor.')]),

  h3('6. Non-Conforming Production'),
  p('If Releasee delivers footage that fails to satisfy any element of Section 2, Releasor shall so notify Releasee in writing, identifying the deficiency. Releasee shall have seven (7) calendar days from that notice to cure, and the Deadline shall be deemed extended solely for that purpose. If the deficiency is not cured within that period, Section 5 applies. Releasor’s acceptance or review of non-conforming footage shall not constitute a waiver of any deficiency or cause this Release to take effect.'),

  h3('7. No Admission'),
  p('This Release is a compromise of a disputed matter. Neither this Release, nor the production of the Video, nor any negotiation or communication concerning either, constitutes or shall be construed as an admission by Releasee of liability, fault, negligence, or the existence of any defective or dangerous condition, all of which Releasee expressly denies. Nor shall anything herein constitute an admission by Releasor that any claim arising from the Incident lacks merit.'),

  h3('8. No Monetary Consideration'),
  p('Releasor acknowledges that the sole consideration for this Release is production of the Video, that no payment of money has been made or promised by Releasee, and that Releasor has not requested any payment.'),

  h3('9. Unknown Claims and Injuries'),
  p('Releasor understands and accepts that injuries sustained in the Incident may prove more serious than presently known, that facts material to this Release may later be discovered to be different from what Releasor now believes, and that upon the occurrence of the Triggering Event this Release extends to all such claims and injuries nonetheless. Releasor has considered this risk and expressly assumes it.'),

  h3('10. Preservation Obligations Survive'),
  p('Nothing in this Release relieves Releasee of any obligation to preserve evidence relating to the Incident, and those obligations remain in effect unless and until the Triggering Event occurs.'),

  h3('11. Governing Law; Construction'),
  p('This Release is governed by the laws of the State of Florida, without regard to conflict-of-laws principles. Venue for any dispute concerning this Release lies in Miami-Dade County, Florida. This instrument shall not be construed against either party as drafter.'),

  h3('12. Entire Agreement; Severability; Counterparts'),
  p('This Release constitutes the entire agreement of the parties concerning its subject matter and supersedes all prior discussions. If any provision is held unenforceable, the remainder shall continue in effect, except that Sections 1, 2, and 5 are essential terms and are not severable — if any of them is held unenforceable, this Release shall be void in its entirety. This Release may be executed in counterparts and by electronic signature.'),

  h3('13. Voluntary Execution'),
  p('Releasor has read this Release in full, understands it, has had the opportunity to consult with an attorney of Releasor’s choosing, and executes it voluntarily.'),
  spacer(120),

  box([pc([b('DO NOT SIGN OR DELIVER THIS INSTRUMENT UNTIL CONFORMING VIDEO HAS ACTUALLY BEEN RECEIVED AND REVIEWED.')], { after: 0 })]),
  spacer(300),

  pl([b('RELEASOR:')], { after: 400 }),
  pl(SIGLINE, { after: 0 }),
  pl('Keith Vallone', { after: 0 }),
  pl('Date: ______________________', { after: 400 }),

  pl('STATE OF ______________________  )', { after: 0 }),
  pl('COUNTY OF ____________________  )', { after: 200 }),
  p('Sworn to (or affirmed) and subscribed before me by means of ☐ physical presence or ☐ online notarization, this ______ day of ______________, 20____, by Keith Vallone, who is ☐ personally known to me or ☐ produced ______________________ as identification.'),
  spacer(300),
  pl(SIGLINE, { after: 0 }),
  pl('Notary Public, State of ______________________', { after: 0 }),
  pl('My commission expires: ______________________', { after: 0 }),
  pageBreak(),
);

// ---------- DOCUMENT 3 — AMERICAN AIRLINES ----------
A(
  pl([b('Keith Vallone')], { after: 0 }),
  pl([fill('[Street address]')], { after: 0 }),
  pl([fill('[City, State ZIP]')], { after: 0 }),
  pl([fill('[Phone]'), run('  |  '), fill('[Email]')], { after: 240 }),
  pl([fill('[Date]')], { after: 200 }),
  pl([b('VIA CERTIFIED MAIL, RETURN RECEIPT REQUESTED, AND ELECTRONIC MAIL')], { after: 200 }),
  pl('American Airlines, Inc.', { after: 0 }),
  pl('Attn: Customer Relations and Legal Department', { after: 0 }),
  pl('1 Skyview Drive, MD 8B503', { after: 0 }),
  pl('Fort Worth, Texas 76155', { after: 220 }),
  pl([b('RE:  EVIDENCE PRESERVATION NOTICE AND REQUEST FOR RECORDS — Passenger fall at Miami International Airport, July 27, 2026 | Ticket 0012363031275 | PNR OYRTCS | AA 4072 CZM–MIA')], { after: 200 }),

  pl('To Whom It May Concern:'),
  p([run('On July 27, 2026, I was traveling on American Airlines under the ticket and record locator above, from Cozumel to Miami on Flight 4072 and continuing from Miami to New Orleans. During my connection at Miami International Airport, I fell on an escalator at approximately '), fill('6:35 p.m. Eastern time'), run(' at or near '), fill('[location]'), run('.')]),
  p([run('I fell roughly twenty minutes after leaving the aircraft. Flight 4072 was scheduled to arrive at 6:06 p.m. Eastern time, which places the incident at approximately '), fill('6:30 p.m. to 6:45 p.m.'), run(' American knows the actual gate arrival time for that flight and I do not, which is why Item 4 of my requests below asks for it. Please treat American’s own record of that arrival as the authoritative anchor for the time of this incident rather than my estimate, and search accordingly.')]),
  p('I am writing to place American Airlines on notice of its obligation to preserve evidence relating to this incident and to request records. My purpose is to obtain a video record of what happened, not to bring a claim against the airline, and I have made a parallel request to the Miami-Dade Aviation Department.'),

  h2('Preservation Notice'),
  p('Litigation arising from this incident is reasonably anticipated. Please suspend any automatic deletion or retention cycle and preserve the following, to the extent within American’s possession, custody, or control:'),
  li('All surveillance or camera footage depicting the location of the incident, including footage from any camera operated by American or by a contractor in any American-leased or American-controlled area of the airport, for four hours before and after the incident;', 'n4'),
  li('All incident, injury, irregularity, or safety reports concerning the incident, however titled, and any entry in a safety or incident reporting system;', 'n4'),
  li('All internal communications concerning the incident, including email, messaging, radio and dispatch logs, and station operations records;', 'n4'),
  li('All records identifying American personnel or contracted personnel — including wheelchair, ground handling, and customer service staff — who were assigned to or present in the area at the time;', 'n4'),
  li('All records of my movements and services on that date, including gate assignments, arrival and departure times for both flights, boarding scan records, and any special-assistance or wheelchair service records associated with my reservation; and', 'n4'),
  li('All records of prior falls or injuries reported in the same area in the preceding sixty months.', 'n4'),

  h2('Requests'),
  p('I request that American provide me with:'),
  li('A copy of any incident or injury report concerning this incident, and its reference number;', 'n5'),
  li('Any surveillance footage of the incident in American’s possession or control;', 'n5'),
  li('Confirmation of whether the location of the incident was within an area leased to, operated by, or controlled by American, and if not, identification of the entity that controls it; and', 'n5'),
  li('The precise arrival time of Flight 4072 at the gate on July 27, 2026, and the gate assignments for both segments of my itinerary, which will help fix the time window of the incident.', 'n5'),
  p('Item 3 matters even if American holds no footage at all: identifying the correct custodian is useful to me and costs American nothing.'),
  p('As my journey that day was international carriage originating in Mexico, I note that the Convention for the Unification of Certain Rules for International Carriage by Air (the Montreal Convention) may govern claims for accidents occurring in the course of disembarking, and that it imposes a two-year limitation period. I raise this to preserve the point and to explain the urgency of my request, not to assert a claim at this time.'),
  p('Please respond within twenty-one (21) days. I am glad to discuss this informally with anyone at American who can help me locate the footage.'),
  spacer(240),
  pl('Respectfully,', { after: 400 }),
  pl(SIGLINE, { after: 0 }),
  pl([b('Keith Vallone')], { after: 0 }),
  pageBreak(),
);

// ---------- DOCUMENT 4 — CBP FOIA ----------
A(
  pl([b('Keith Vallone')], { after: 0 }),
  pl([fill('[Street address]')], { after: 0 }),
  pl([fill('[City, State ZIP]')], { after: 0 }),
  pl([fill('[Phone]'), run('  |  '), fill('[Email]')], { after: 240 }),
  pl([fill('[Date]')], { after: 200 }),
  pl('U.S. Customs and Border Protection', { after: 0 }),
  pl('FOIA Division', { after: 0 }),
  pl('1300 Pennsylvania Avenue NW, Mail Stop 1181', { after: 0 }),
  pl('Washington, DC 20229', { after: 0 }),
  pl([run('Also submitted electronically via the CBP FOIA portal at ', { size: 20 }), new TextRun({ text: 'foia.cbp.gov', italics: true, size: 20 })], { after: 220 }),
  pl([b('RE:  FREEDOM OF INFORMATION ACT REQUEST AND RECORDS PRESERVATION REQUEST — Surveillance video, Federal Inspection Area, Miami International Airport, July 27, 2026')], { after: 200 }),

  pl('To the FOIA Officer:'),
  p('Pursuant to the Freedom of Information Act, 5 U.S.C. § 552, and the Privacy Act, 5 U.S.C. § 552a, I request records concerning myself and an incident in which I was involved.'),

  box([p([
    b('Send this letter.'),
    run(' Falling about twenty minutes after leaving an international arrival places you inside or immediately adjacent to the federal inspection area. Cameras in that zone belong to CBP, and the airport cannot produce that footage no matter how cooperative it is — it does not own it. Send this even if you believe you had already cleared customs: a FOIA request costs nothing but postage, and a "no records" response definitively narrows the search to the County.'),
  ], { after: 0 })]),
  spacer(200),

  h2('Requester Information'),
  kvTable([
    ['Full legal name', 'Keith Vallone'],
    ['Date of birth', [fill('[DOB]')]],
    ['Place of birth', [fill('[place]')]],
    ['Citizenship', [fill('[citizenship]')]],
    ['Passport number', [fill('[passport no.]')]],
    ['Date and port of entry', 'July 27, 2026 — Miami International Airport (MIA)'],
    ['Arriving flight', 'American Airlines 4072 from Cozumel, Mexico'],
    ['Ticket / PNR', '0012363031275 / OYRTCS'],
  ]),
  spacer(200),

  h2('Records Requested'),
  p('For the date of July 27, 2026, at Miami International Airport:'),
  li([run('All closed-circuit television or other video recordings from any camera within the Federal Inspection Area, Customs and Border Protection primary or secondary inspection areas, or the arrivals corridor between the aircraft arrival gate and the exit from the federal inspection area, covering the period from '), fill('4:00 p.m.'), run(' to '), fill('9:00 p.m.'), run(' Eastern time, and specifically any footage depicting an escalator at or near '), fill('[location]'), run(' and any footage depicting me falling on an escalator. American Airlines Flight 4072 from Cozumel was scheduled to arrive at 6:06 p.m. Eastern time and I fell approximately twenty minutes after deplaning; the window above is stated broadly because I do not know the flight’s actual arrival time, which CBP can establish from the records requested in Item 2 below;')], 'n6'),
  li('All records of my inspection, admission, and processing on that date, including my arrival record and any TECS or Automated Passport Control transaction records, which will establish the precise times at which I entered and exited the federal inspection area;', 'n6'),
  li('All incident, injury, or assistance reports generated by CBP personnel relating to a passenger fall at that location on that date; and', 'n6'),
  li('All communications between CBP and the Miami-Dade Aviation Department, airport operations, emergency medical services, or American Airlines concerning such an incident.', 'n6'),

  h2('Preservation Request'),
  p('I request that CBP immediately preserve all records responsive to this request, and in particular the video described in Item 1, and suspend any automatic overwrite or destruction cycle applicable to it pending the resolution of this request and any administrative appeal. Video systems of this kind commonly overwrite within a short period, and the records I seek may cease to exist during ordinary FOIA processing if they are not affirmatively held.'),

  h2('Expedited Processing'),
  p([run('I request expedited processing on the ground that there is an urgency to inform the requester concerning an actual or alleged loss of a substantive due process right, and, independently, because the responsive video is subject to imminent automatic destruction such that ordinary processing would render this request futile. '), fill('[If you have been injured, add: I sustained physical injury in this incident and require the footage to document how it occurred.]')]),
  p('I certify that the foregoing is true and correct to the best of my knowledge and belief.'),

  h2('Fees'),
  p([run('I am requesting these records for personal, non-commercial use as the subject of the records. I agree to pay reasonable processing and duplication fees up to $'), fill('[e.g., 100]'), run('. Please contact me before incurring charges beyond that amount.')]),

  h2('Segregability'),
  p('If any portion of a responsive record is withheld, please release all reasonably segregable non-exempt portions and provide the specific exemption claimed for each withholding along with a brief explanation. I do not seek camera positions, coverage areas, security procedures, or law enforcement techniques, and I consent to redaction of any such material and of the images of other travelers and of CBP personnel.'),

  h2('Certification of Identity'),
  p('A signed and notarized Certification of Identity (DHS Form 590) is enclosed, together with a copy of my photo identification, in support of the Privacy Act portion of this request.'),
  spacer(240),
  pl('Respectfully,', { after: 400 }),
  pl(SIGLINE, { after: 0 }),
  pl([b('Keith Vallone')], { after: 240 }),
  pl([b('Enclosures: '), run('DHS Form 590 (Certification of Identity, notarized); copy of photo identification; copy of ticket and itinerary.')]),
  pageBreak(),
);

// ---------- DOCUMENT 5 — 768.28 NOTICE ----------
A(
  box([pc([b('HOLD IN RESERVE — SEND ONLY IF THE DEADLINE IN DOCUMENT 1 PASSES')], { after: 0 })]),
  spacer(200),
  p([run('Serving this notice is a formal legal act with consequences: it opens the statutory pre-suit investigation period and signals that you intend to pursue a claim. It also protects your rights, because a claim against a Florida agency generally cannot proceed without it and the statute imposes hard deadlines. Have an attorney review it before service, confirm the current filing requirements and the applicable limitations period, and note that notice must go both to the agency and to the Florida Department of Financial Services.', { size: 20, color: '4A4F57' })]),
  spacer(200),

  pl([b('Keith Vallone')], { after: 0 }),
  pl([fill('[Street address]'), run('  |  '), fill('[City, State ZIP]')], { after: 0 }),
  pl([fill('[Phone]'), run('  |  '), fill('[Email]')], { after: 240 }),
  pl([fill('[Date]')], { after: 200 }),
  pl([b('VIA CERTIFIED MAIL, RETURN RECEIPT REQUESTED')], { after: 200 }),
  pl('Florida Department of Financial Services', { after: 0 }),
  pl('Bureau of Risk Management — Division of Risk Management', { after: 0 }),
  pl('200 East Gaines Street, Tallahassee, Florida 32399', { after: 180 }),
  pl([i('and')], { after: 0 }),
  pl('Miami-Dade County — Office of the County Attorney / Risk Management', { after: 0 }),
  pl('111 N.W. First Street, Suite 2810, Miami, Florida 33128', { after: 220 }),
  pl([b('RE:  NOTICE OF CLAIM PURSUANT TO §768.28(6), FLORIDA STATUTES')], { after: 200 }),

  kvTable([
    ['Claimant', [run('Keith Vallone, '), fill('[address]'), run(', DOB '), fill('[DOB]')]],
    ['Agency', 'Miami-Dade County / Miami-Dade Aviation Department'],
    ['Date of loss', 'July 27, 2026'],
    ['Time', [run('Approximately '), fill('6:30 p.m. – 6:45 p.m. Eastern time')]],
    ['Place', [run('Miami International Airport — '), fill('[precise location]')]],
  ]),
  spacer(200),

  p('Please take notice that the undersigned asserts a claim against Miami-Dade County arising from personal injuries sustained on July 27, 2026, at Miami International Airport.'),
  p([b('Statement of the claim.'), run(' On the above date and time, Claimant, a lawful invitee traveling through Miami International Airport between connecting flights, fell while riding an escalator located at '), fill('[location]'), run('. '), fill('[Insert factual description of the fall and of the condition believed to have caused it.]'), run(' Claimant alleges that the County, as owner and operator of the premises, failed to maintain the escalator in a reasonably safe condition, failed to inspect and repair it, and failed to warn of a dangerous condition of which it knew or should have known in the exercise of reasonable care.')]),
  p([b('Injuries and damages. '), fill('[Describe injuries, treatment received, providers, and known or anticipated damages including medical expenses, lost wages, and pain and suffering. State that the investigation is ongoing and damages are continuing.]')]),
  p([b('Prior request and preservation notice.'), run(' On '), fill('[date of Document 1]'), run(', Claimant delivered to the Miami-Dade Aviation Department a written evidence preservation notice and public records request seeking the surveillance video of this incident, together with an offer to release all claims in exchange for its production. The County did not produce conforming video by the stated deadline. Claimant’s preservation demands set forth in that letter remain in effect and are reasserted here in full.')]),
  p([b('Renewed offer.'), run(' Claimant’s willingness to resolve this matter on production of the video has not changed. Claimant remains prepared to execute a full and final release, without any payment by the County, upon delivery of the complete surveillance footage of the incident. This notice is served to preserve Claimant’s rights, not to foreclose that resolution.')]),
  p([run('This notice is given pursuant to §768.28(6), Florida Statutes. Claimant has not attempted to settle this claim with any other party except as stated herein and receives no benefits from the Medicaid program '), fill('[confirm or amend this statement — do not send it if inaccurate]'), run('.')]),
  spacer(300),
  pl(SIGLINE, { after: 0 }),
  pl([b('Keith Vallone'), run(', Claimant')], { after: 300 }),
  p([run('This packet is a drafting aid prepared without the involvement of an attorney. It is not legal advice and creates no attorney–client relationship. Verify all statutory citations, deadlines, and filing requirements with Florida-licensed counsel before relying on them.', { size: 19, color: '4A4F57' })]),
);

// ============================================================
const doc = new Document({
  creator: 'Keith Vallone',
  title: 'MIA Escalator Incident — Evidence Preservation and Video Production Packet',
  description: 'Demand packet for production of surveillance video, MIA, July 27, 2026',
  styles: {
    default: {
      document: { run: { font: 'Times New Roman', size: 24, color: '000000' } },
    },
    paragraphStyles: [
      {
        id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { font: 'Times New Roman', size: 25, bold: true, color: '000000' },
        paragraph: {
          spacing: { before: 320, after: 140 },
          border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: 'C9CED6', space: 4 } },
        },
      },
      {
        id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { font: 'Times New Roman', size: 24, bold: true, color: '000000' },
        paragraph: { spacing: { before: 240, after: 100 } },
      },
    ],
  },
  numbering: {
    config: [
      decConfig('n1'), decConfig('n2'), decConfig('n3'),
      decConfig('n4'), decConfig('n5'), decConfig('n6'),
      alphaConfig('alpha1'),
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: PAGE_W, height: PAGE_H },
        margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN },
      },
    },
    children: kids,
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(process.argv[2], buf);
  console.log('wrote', process.argv[2], buf.length, 'bytes');
});
