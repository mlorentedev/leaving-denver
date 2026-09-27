# Vehicle Sale Runbook: 2019 Ford Escape SEL AWD

How the car is sold safely in Colorado. The seller needs the car until the last days before the 2026-11-09 departure, so the sale is agreed early and the car is handed over later.

Owner decisions are marked **[OWNER]**. Everything else is procedure. Sources are at the end. Never commit a filled-in copy of the agreement, the plate number or the buyer's details: this repo is public.

## 1. Before listing

- [ ] Listing copy states only what the documents back (`test_no_unbacked_vehicle_claims`). There is no 100k service receipt, so the listing never claims that service.
- [ ] The odometer in the listing matches the dashboard. The recall invoice already shows 102,692 mi on 2026-09-25.
- [ ] Instant offers pulled (CarMax, Carvana, KBB ICO, Peddle) to know the floor. They expire in 7 days, so pull them again around Nov 1–2 (OPS-002 #27).
- [ ] Title in hand, no lienholder. Keep it at home; it only leaves home on handover day.
- [ ] AirCare test booked for the days just before handover, not now (OPS-008 #33). See §6.

## 2. First contact and screening

Move on without arguing when you see any of these:

- **Overpayment.** The buyer offers a check for more than the price and asks for the difference back. This is the classic fake-check scam.
- **Remote purchase.** The buyer is abroad, deployed or "at sea", or sends a shipper, or wants to pay before seeing the car.
- **Your report, their link.** The buyer asks you to buy a Carfax or other VIN report on a site they send. Point them to the official checks: NHTSA recalls by VIN, and NICB VINCheck.
- **Verification code.** The buyer asks for a code sent to your phone. That is Google Voice or account takeover. Never read out a code.
- **Their escrow site.** The buyer proposes an escrow or payment site they chose. The only platforms are the ones in §4, reached by typing their address yourself.
- **Deposit request.** The buyer wants to send a deposit before seeing the car, or asks you to send money for any reason.

A real buyer will do all of the following. Ask for it before the first meeting:

- Give a name and a call-back number.
- Come in person.
- Accept that payment happens at a bank (§5).

## 3. Showing, test drive and inspection

- **Where.** Start from a busy public lot, not the apartment, and meet in daylight.
  - No safe exchange zone is confirmed for Centennial or Arapahoe County. Call the Sheriff's non-emergency line (303-795-4711) to ask whether their HQ lot at 13101 E. Broncos Pkwy can be used.
  - Denver PD has marked Safe Trade Zones at district stations. Confirm they still exist before relying on one.
- **Who.** One buyer, plus at most one companion, and you. Tell someone where you are and when you expect to be back.
- **Before handing over the keys:**
  - Photograph the buyer's driver's license and insurance card.
  - Sit in the passenger seat. The buyer never drives alone.
- **Pre-purchase inspection (PPI).** Welcome it.
  - The buyer picks and pays the shop. You drive the car there and stay.
  - Suggest the buyer ask for a cooling-system pressure test and a combustion-gas (block) test. These are Ford's own checks for the known 1.5L coolant issue, and a clean result is your best answer to it.
- **What to show:**
  - the recall invoice with the dealer inspection;
  - the emissions report;
  - the title (they can look, but it stays in your hand).
- **What never to hand over:** the registration card or the title for photos. Both show your name and address.

## 4. Agreeing the sale before handover

The buyer agrees now and takes the car around Nov 6–7 **[OWNER: exact date]**. Write the agreement down, using the Appendix.

### 4.1 Deposit: two options **[OWNER: pick one]**

No escrow product locks a buyer in with a non-refundable deposit.

- **KeySavvy** holds the buyer's payment, but that payment is refundable until pickup, so it does not lock the buyer.
- **KeySavvy for the whole sale** is a poor fit for this timeline too. It pays the seller only once the title has been mailed to KeySavvy and the buyer has picked up the car. With handover Nov 6–7 and departure Nov 9, the mail is the failure mode.

| Option | How | Seller risk | Buyer risk |
|---|---|---|---|
| **A. Signed deposit** | $300–500 paid to you in person (Zelle confirmed in *your* bank app, or cash) against the signed agreement. The deposit counts toward the price. It is kept if the buyer walks away, and returned in full if you do or if the car is lost or damaged (§4.2). | Low | The buyer trusts you with the deposit. Some buyers will refuse. |
| **B. No deposit** | Price and date agreed in writing, and nothing paid until handover. You keep showing the car to a backup buyer. | The buyer can vanish. Covered by the CarMax re-pull ~Nov 1–2 and an in-store appraisal ~Nov 2. | None |

### 4.2 Terms the agreement must include

- **Price** (locked, no later renegotiation) and **handover date**, with a fallback date.
- **Condition:** as-is, the PPI already done, and the car handed over as it was at the PPI apart from normal driving. State the odometer reading at signing and an allowance for miles until handover.
- **Risk of loss:** it stays with the seller until handover. If the car is damaged, a full refund or a price reduced by agreement. If it is totalled or stolen, a full refund. The seller's insurance stays in force until then.
- **If either side walks away:** say what happens to the deposit (option A).
- **Payment at handover:** the method in §5, and nothing else.

## 5. Handover day, in this order

Plan it at least two banking days before departure, so a problem still has time to be fixed.

1. **At the buyer's bank:**
   - Watch the teller issue a cashier's check drawn on that bank, payable to you, for the balance.
   - The alternative is a wire to your account. It only counts once it shows as *posted* in your own banking app, not as pending, and not in an email.
   - Never accept a cashier's check the buyer brings already printed. If you must, verify it by calling the issuing branch on a number you looked up yourself.
2. **Only now, the title:**
   - Sign as seller, with the date, the price and the odometer reading from the dashboard that day.
   - Every owner listed on the title signs.
3. **DR 2173 bill of sale:** two copies, both sign both, one each. It must show the year, make, VIN, the date and time of sale, and both signatures. The buyer needs it to drive home.
4. **Hand over:**
   - keys and fobs;
   - the new, unused emissions certificate (§6);
   - the recall invoice.
5. **Photograph** the signed title (both sides), both bills of sale, the buyer's license, and the dashboard odometer.
6. **Remove the plates.** In Colorado they belong to the seller.
   - The buyer may drive home for up to 36 hours with the signed bill of sale and insurance **in the buyer's own name**. Tell them beforehand to bring proof of that insurance.
   - Also remove the toll transponder, if any.
7. **Clear your data from the car:**
   - the SYNC paired phones and contacts;
   - the HomeLink garage codes, if any are set;
   - FordPass (remove the vehicle from your account);
   - the saved navigation home address.
8. **The same day, file the Report Release of Liability** on mydmv.colorado.gov. It needs the plate number and the VIN, and the law gives 5 days. Save the confirmation.
9. **Deposit the check at your own bank.**
   - A cash deposit over $10,000 generates a routine Currency Transaction Report. That is normal. **Never split a deposit to avoid it**: splitting is itself a crime (structuring).
   - Keep the US account open until the funds have fully cleared, not just become "available".

## 6. Emissions

The May 2026 certificate was used for the seller's own renewal, so it does not count for the sale (CO DMV). Test at AirCare in the days before handover and give the buyer the new certificate.

A car that fails emissions within 5 business days of sale can be returned by the buyer. A fresh passing test at sale closes that risk while the seller is abroad.

## 7. After the sale

- **Insurance:** cancel it only after the title is signed, the plates are off and the release is filed. Ask the insurer for a cancellation letter showing claim-free years; it helps with insurance abroad.
- **Plates:** turn them in at the county office or a metal recycler, and do it before Nov 9.
- **Records:** keep the photos from §5 and the release confirmation somewhere you can reach from abroad.

## 8. If it has not sold

- **Nov 1–2:** pull the instant offers again (§1).
- **Around Nov 2:** a CarMax in-store appraisal holds for 7 days, which covers the departure. Selling to CarMax still follows §5 steps 5–9.

## Appendix: agreement template

Print it, fill it in by hand, and never commit a filled-in copy.

```
VEHICLE SALE AGREEMENT (DELAYED HANDOVER)

Vehicle: 2019 Ford Escape SEL AWD, VIN 1FMCU9HD9KUB80146
Seller: ____________________   Buyer: ____________________ (ID no. ________)

Price: $________ , locked. Deposit received today: $________ (method: ______),
credited toward the price. Balance due at handover: $________ .

Handover: ____ / ____ / 2026 at ______ ; fallback date ____ / ____ / 2026.
Balance paid at handover by cashier's check issued in the Seller's presence at
the Buyer's bank, or by wire posted to the Seller's account before the title is signed.

Condition: sold AS-IS. Pre-purchase inspection done on ____ / ____ / 2026 at
______________________. Odometer today: ________ mi; handover allowance: ______ mi.

Risk of loss stays with the Seller until handover. If the vehicle is lost, stolen
or totalled before then, the deposit is refunded in full. If it is damaged, the
Buyer may take a full refund or a price reduced by written agreement.

If the Buyer does not complete the purchase by the fallback date, the Seller keeps
the deposit. If the Seller does not complete it, the Seller refunds the deposit in full.

Seller signature / date: ____________________
Buyer signature / date:  ____________________
```

## Sources

- CO DMV, private sale: https://dmv.colorado.gov/buying-and-selling
- CO DMV, release of liability (C.R.S. 42-6-109(3)): https://dmv.colorado.gov/colorado-residents-now-able-to-voluntarily-report-vehicle-ownership-transfers
- Douglas County, plates and the 36-hour rule: https://www.douglasco.gov/motorvehicle/buying-or-selling-a-vehicle/
- FTC, "cleared" checks: https://www.ftc.gov/news-events/data-visualizations/data-spotlight/2020/02/dont-bank-cleared-check
- FDIC, fake checks: https://www.fdic.gov/consumers/consumer/news/august2019.html
- KeySavvy, how it works: https://www.keysavvy.com/how-it-works
- Arapahoe County Sheriff: https://www.arapahoeco.gov/your_county/county_departments/sheriffs_office/
- Vault research: `10_projects/leaving-denver/research/2026-09-25-vehicle-sale-escape.md`
