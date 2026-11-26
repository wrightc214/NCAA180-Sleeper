# App asset pipeline review

Merge the [Asset migration PR](https://github.com/wrightc214/NCAA180-Assets/pull/2) first.
Wait for both implementation PRs to merge before dispatching Asset promotion.

- App baseline `b6faeb8304791225a2d99742a7024ed0011f2b1e`
- Verified Asset migration commit `d16308612c0a6efb98a23f06b8f704f21b56ae62`

The Git-tree audit matched all 562 raw App blobs to their identical Asset destinations.
App history retains earlier revisions.

## Reviewer commands

```sh
python -m pip install Pillow==12.3.0 pytest
python -m pytest tests/test_logo_trim.py
python scripts/audit_raw_art.py ../asset
python scripts/logo_trim.py
```

The final command checks the six configured folders against the current site artwork.
Any failing legacy logo blocks glow generation until a compliant web copy is promoted.
The workflow's sole direct main write stages and commits generated team glow.

## Removed raw artwork

| App path | Original App blob ID | Asset path | Verification |
| --- | --- | --- | --- |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/acc 1953-1978.png` | `051b8b4ced42995be54ad121dbffc4d963a9bf11` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/acc 1953-1978.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/acc 1978-1987.png` | `d4f8d429b8dab5051f704ea8055d1a7aa7c494e6` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/acc 1978-1987.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/acc 1987-1991.png` | `f8ae3bcadc4d0fb9b9524095df688ed791db3c96` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/acc 1987-1991.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/acc 1991-1997.png` | `9a89599ac327fe65bf520f33df5c97d72fac0c52` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/acc 1991-1997.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/acc 1997-2005.png` | `9fe3bdb6d4da37729f82f5224b03ddf242cf9647` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/acc 1997-2005.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/acc 2005-2014.png` | `8db5f0b3c992b4854429a0784826eee1c976f6cb` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/acc 2005-2014.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/america east 1996-2008.png` | `baff537c5b142100b5f32669fa99bac66d12a0cf` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/america east 1996-2008.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/america east 2008-2013.png` | `5e3d3f8919cd031087f932fde097d0e052beabde` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/america east 2008-2013.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/america east 2013-2024.png` | `cc6c0dd3f3702bf198833cc2b9435f2372e5d3e6` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/america east 2013-2024.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/american 2013-2016.png` | `349dfa12a573bec29dcc015866300dbdc8b9999f` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/american 2013-2016.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/american 2016-2017.png` | `8e78b7e1b5e338ea1876f8ab7809342b11b7833b` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/american 2016-2017.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/atlantic 10 1982-1995.png` | `5d60ff77a72640254997a7e8198b2e6d3084477d` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/atlantic 10 1982-1995.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/atlantic 10 1995-2003.png` | `55f0f29bf84b2346b1cf5df51339c30cdb65130e` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/atlantic 10 1995-2003.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/atlantic 10 2003-2014.png` | `456c23daaadab49283d07c945ea71ee9095428ac` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/atlantic 10 2003-2014.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/atlantic sun 2000-2015.png` | `c32efa7354e0b0e7ab3996c4bc128e97fb1838ef` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/atlantic sun 2000-2015.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/big 12 1996-2004.png` | `ada8b9da9acf8bc0194ec0768479e9f3ae554b3a` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/big 12 1996-2004.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/big 12 2003-2014.png` | `9c1019483809579bff64a7a8c68940b29892f49a` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/big 12 2003-2014.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/big 12 2014-2026.png` | `ffcfc636f2e991bc138f0470d56b98bcbbd04c01` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/big 12 2014-2026.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/big east 1979-1998.png` | `f60a21251f92a3c2d9fb22c00057e47a9d0200d2` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/big east 1979-1998.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/big east 1998-2005.png` | `d165ef0121371eae63c90cf1d4522ecce49de93f` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/big east 1998-2005.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/big eight.png` | `1713ad533fc300f42aaf21fea0119046418c0e53` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/big eight.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/big sky 1970-1996.png` | `01a44deae3f2c94115ae00c4f03008d35c1080ce` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/big sky 1970-1996.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/big sky 1996-2012.png` | `4295cecdc60cf648df44a47585586aa273005e3d` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/big sky 1996-2012.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/big south 1983-1998.png` | `05dd1c7b81a7c12ffd7eeeb36a569daf662c6ca8` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/big south 1983-1998.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/big south 1998-2006.png` | `da9c8e558f425eb8b19823ff86590b29b0326829` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/big south 1998-2006.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/big south 2006-2012.png` | `46538ed99a4ed452cbd88d19d2a0074190d660fd` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/big south 2006-2012.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/big south 2012-2017.png` | `feddb5d82990c8b565bc591f8cb9bb0023b419da` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/big south 2012-2017.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/big ten 1970-1984.png` | `02c10eb0e78a80970d6ee16266f4999cd19734fb` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/big ten 1970-1984.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/big ten 1985-1991.png` | `22b58bd04831e0393ace83178bb01c07bacca1cd` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/big ten 1985-1991.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/big ten 1992-2011.png` | `68334762b8458d6b0d4b4874e204dd4d10b153cc` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/big ten 1992-2011.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/big west 1988-1995.png` | `c12ded7f6b95076df7e89d8645542c15d0f5c075` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/big west 1988-1995.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/big west 1995-2005.png` | `a99aafbbe6c1b19ea9f230d7115cd5ace03045c8` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/big west 1995-2005.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/big west 2005-2016.png` | `c2c87e0b730783a701ce391efe3ea642cc09c7c0` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/big west 2005-2016.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/big west 2016-2021.png` | `13f1983bad32a0bb440ac6b386aa545e1db1a58d` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/big west 2016-2021.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/caa 1985-2003.png` | `fb4c77733ab190eb98b2010d40755a56f853c518` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/caa 1985-2003.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/caa 2003-2013.png` | `7cb83607c4c97fa101925878bebcfcffc126e669` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/caa 2003-2013.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/caa 2013-2019.png` | `8f04bd6ac88d43a5ccc6220c020ea46a7852e973` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/caa 2013-2019.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/conference usa 1995-2000.png` | `5ae551daee61e9b9debe33bbb0f6ffb34191bb96` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/conference usa 1995-2000.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/conference usa 2000-2002.png` | `c6f35241979c7496f8715d46f983c959f7cd0477` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/conference usa 2000-2002.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/conference usa 2003-2005.png` | `92b7c760aca210b4855daf4c7b88717f0aebe3a8` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/conference usa 2003-2005.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/conference usa 2005-2012.png` | `bab6855f90553a11f95b63bcd201e63ac2314000` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/conference usa 2005-2012.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/conference usa 2013-2022.png` | `75e41fb823c650e70f4a44489f2b245326054f7e` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/conference usa 2013-2022.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/conference usa 2023.png` | `340fa18c50f40fc12d866ed9c0eb2cf08283f5e9` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/conference usa 2023.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/east coast conference shield.png` | `e1340bacd9f9804c244c384bbfcd76b601f2a73e` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/east coast conference shield.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/east coast conference.png` | `1413ac129325017d16074042346826d96fe1baec` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/east coast conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/great west.png` | `b18416b5791ca5d97e138be667cb7c316434b036` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/great west.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/horizon league 2001-2014.png` | `1439be0b2103201f8c79cf7f578eb4cdcf70bd38` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/horizon league 2001-2014.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/horizon league 2014-2023.png` | `b861097cb476c1f37209a1f374bb0e6e3daddb83` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/horizon league 2014-2023.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/ivy league 1982-2019.png` | `aa174df818cc722ecb7a112d561ba850706a8d18` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/ivy league 1982-2019.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/maac 1980-1983.png` | `46f30c953af426523a1a9c30410bdb1c0cbf1f4e` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/maac 1980-1983.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/maac 1983-1987.png` | `18b334c93260b1454a5bde36892e534ded7dfc5b` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/maac 1983-1987.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/maac 1987-1995.png` | `455e5e63de060fa3eada32c18c8d04c02e724fe9` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/maac 1987-1995.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/maac 1995-2003.png` | `dbd97769710c3a3653a672b8194c5b107da51257` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/maac 1995-2003.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/maac 2003-2023.png` | `7e8b371149bc2665d1d901db7e16c1f53366f93e` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/maac 2003-2023.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/mac 1946-1987.png` | `504f4f37043fd427070fec38dbaa7c0cbce98f4f` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/mac 1946-1987.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/mac 1987-2001.png` | `495a23a445eb643ef805affcd21cb7d19da513b6` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/mac 1987-2001.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/mac 2001-2008.png` | `a0c78fb9300ae568201105ce7c36471e1bc3d3e6` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/mac 2001-2008.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/meac 1970-2004.png` | `7b9a984b28d632a3845a7587cc787a73caf40aa8` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/meac 1970-2004.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/meac 2004-2012.png` | `4e88827d880e010b9e845a830f361e81fcf95f2d` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/meac 2004-2012.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/meac 2012-2018.png` | `ddea1003c0409e2ef6d1bb5379610f3b36f33111` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/meac 2012-2018.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/metro conference.png` | `43e712d2bc573eaf1f6c768942b71ab687fcb8b6` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/metro conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/mid continent.png` | `7511d456d138f6172a8cec9beaa8d93d5af56b85` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/mid continent.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/missouri valley 1907-1948.png` | `69d69670c699b736107e120a72074ab70de50b29` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/missouri valley 1907-1948.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/missouri valley 1948-1966.png` | `1ed2ade2e3c322a3c30ea3dfddbb490ecfaf0295` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/missouri valley 1948-1966.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/missouri valley 1966-1970.png` | `30abb63217d88bd24da5edda5865b5d00f1c13ea` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/missouri valley 1966-1970.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/missouri valley 1970-1975.png` | `7fb8a426dd09ad5e605a5d95b6a29d38f51f4de8` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/missouri valley 1970-1975.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/missouri valley 1975-1988.png` | `56f73423079b4f60573d395fc8cdd60f38aecd82` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/missouri valley 1975-1988.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/missouri valley mvc.png` | `9b8e4d69621e341a6398ce2cee49d2ce255cdba2` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/missouri valley mvc.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/mountain west 1999-2011.png` | `5be26bcd283b9e7b3c123d4831f3ea0b81ccd2bf` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/mountain west 1999-2011.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/ohio valley 1948-1966.png` | `6c4f7e655b094f19627469b3fedb704288ce0a5a` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/ohio valley 1948-1966.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/ohio valley 1966-1975.png` | `0f2b4e866f8caee73bfc78706f11068629532b5f` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/ohio valley 1966-1975.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/ohio valley 1975-1979.png` | `555e7fec4070368534a7ce405cfcc58d6628b757` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/ohio valley 1975-1979.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/ohio valley 1979-1993.png` | `d67d2ed391f0b37fe4a2ffdc27644458c01208df` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/ohio valley 1979-1993.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/ohio valley 1993-2002.png` | `0cc731415c9ab8fe202a9f830403c02eea7705af` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/ohio valley 1993-2002.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/pac-10 1978-1994.png` | `1d8e05d4ec736ee7131a8413332a08d3b01355fd` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/pac-10 1978-1994.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/pac-10 1995-2009.png` | `c53c0c72f06adf888dc5f1edcc516283c151dcc6` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/pac-10 1995-2009.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/pac-10 2010-2011.png` | `610c27eb583c3b16d44ad2c399a3907f9c2bd699` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/pac-10 2010-2011.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/pac-12 2010-2026.png` | `dcb4914386038130ec9cd22447ebf96b38bc978d` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/pac-12 2010-2026.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/pac-12 circle.png` | `0d00672c1b6197f28c58678379122bc9b36734c5` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/pac-12 circle.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/pac-8.png` | `6c10d2b359920faa1f9d55f8e02590da69fd3166` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/pac-8.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/pacific coast.png` | `b53dc1e7f49b78b71b820746e945ca6d0cbe0d5b` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/pacific coast.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/sec 1932-1964.png` | `12fd71adf70a8e44559bf90dc1d3ff895ad0de55` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/sec 1932-1964.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/sec 1964-1966.png` | `8f448767c886d4fac6efcf1cdcf60b4d85575036` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/sec 1964-1966.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/sec 1966-1970.png` | `9cc683f299d170742de2badd5c296bf6c36e7268` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/sec 1966-1970.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/sec 1970-1988.png` | `e0c6a9634548e0d57432f9696499652d9740676e` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/sec 1970-1988.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/sec 1988-2008.png` | `f6587583d80e1a787df67105c5f148045f16eb21` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/sec 1988-2008.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/sec 2008-2022.png` | `b84b2003819a9cbf442c8b452c378d70b1c4f0fb` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/sec 2008-2022.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/southern 1958-1964.png` | `e09a4f1901878cac6f044a73a51068c3e08c999e` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/southern 1958-1964.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/southern 1964-1999.png` | `3f20307d724ce1e58f171a8b05d9638429726163` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/southern 1964-1999.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/southern 1999-2023.png` | `7c4560f4a587557b667bc6e3c541ada07af8018e` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/southern 1999-2023.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/southland 1963-1972.png` | `c2c28881faee0068c50f0d87e43f942238ce61c4` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/southland 1963-1972.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/southland 1972-2002.png` | `7cd0e5e30e0cf2c0e3e6b41a8315706843bdcccf` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/southland 1972-2002.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/southland 2002-2012.png` | `502abde05fe87813efbb20ab01161626d0da36c7` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/southland 2002-2012.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/southland 2012-2023.png` | `617bb8211a33fdb4a9507cbfacb20da4cc127e18` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/southland 2012-2023.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/sun belt 1976-1980.png` | `43d199235ccb1579f7ce3381988527ceca608ffc` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/sun belt 1976-1980.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/sun belt 1980-1982.png` | `f454b4c2ff386600d4b6944e2edff4a6c89f498b` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/sun belt 1980-1982.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/sun belt 1982-1991.png` | `1f742e26f4a0322d95a00d0386def47a4663b59b` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/sun belt 1982-1991.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/sun belt 1991-1997.png` | `35e5794784a513b34148100c7b16fdce2ba9d5ce` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/sun belt 1991-1997.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/sun belt 1997-2013.png` | `c516078e9ba647e243f2ac5afb337bfcaeb4083e` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/sun belt 1997-2013.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/swac 1979-1982.png` | `b9aafcaa8577f3dfb6ecdf54c0e71f7a9a36f57a` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/swac 1979-1982.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/swac 1982-2001.png` | `ddbc47242d3330c576a7de2ec3d221bb2bece7aa` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/swac 1982-2001.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/swac 2001-2020.png` | `0e6f372943707b3b2b36630ee0ebe891818072c0` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/swac 2001-2020.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/swc.png` | `44b5c7cc7a8bfecd7368d243347a6ea289839b79` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/swc.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/wac 1962-1982.png` | `932f493481fc15d4158a3da76376cc5346cb8c92` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/wac 1962-1982.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/wac 1982-1992.png` | `83cd7e9771dfe8e3596169aadd7ac8387889a204` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/wac 1982-1992.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/wac 1992-2005.png` | `bc00b9b11ff12d80b8d4897efc4df4d29373f0ff` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/wac 1992-2005.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/west coast 1972-1989.png` | `b5cc8ac974a73d677ef42edfb12bf1188d7ff797` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/west coast 1972-1989.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/west coast 1989-1995.png` | `8745f2084497f037d931e06e6124dbbd92be4d8c` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/west coast 1989-1995.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/west coast 1995-2011.png` | `8fd3112b931e698a0f82f56395510130f0ed1fce` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/west coast 1995-2011.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/Throwbacks/west coast 2011-2019.png` | `0ad22d3538e5a9ab81cf52900400a92df5b0c46b` | `Unused/logos/logo jackpot/CCG Logos/Throwbacks/west coast 2011-2019.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/america east.png` | `582bafbf60d1ac5141b792a8b85d8f9f6bbb890f` | `Unused/logos/logo jackpot/CCG Logos/america east.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/appalachian conference.png` | `6a4380d9169f7f1de9a843dc8c0214d54e11a1d5` | `Unused/logos/logo jackpot/CCG Logos/appalachian conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/asun.png` | `b5ece818ce23dcfc9a541fad7626a869e5d99745` | `Unused/logos/logo jackpot/CCG Logos/asun.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/atlantic 10.png` | `a7de31c63ef09521df7cbcbeb8fae42786d3fd26` | `Unused/logos/logo jackpot/CCG Logos/atlantic 10.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/big east.png` | `08ebe373325cfef32879c9845505fe4feeb8216a` | `Unused/logos/logo jackpot/CCG Logos/big east.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/big sky.png` | `312c20f4f201b1b43746c4a50931c3c7b83acd4e` | `Unused/logos/logo jackpot/CCG Logos/big sky.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/big south.png` | `b566397af789c73749b1008e7a414de1314f6b23` | `Unused/logos/logo jackpot/CCG Logos/big south.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/big west.png` | `f76eae3fb7283973bb940fe78f66fc8fa6a00b4c` | `Unused/logos/logo jackpot/CCG Logos/big west.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/caa football.png` | `39b125fee7fad68e21e03ae2e63ec812c4d5fbdd` | `Unused/logos/logo jackpot/CCG Logos/caa football.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/california conference.png` | `2ecae01e70fba02c7a0a77bfcc33fdce3320505b` | `Unused/logos/logo jackpot/CCG Logos/california conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/chesapeake conference.png` | `f0cbc71a01efffbe33ee3b30a0e3370b9a0566b8` | `Unused/logos/logo jackpot/CCG Logos/chesapeake conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/coastal.png` | `7adacc7536b58495185bd5a32544432bd734d22d` | `Unused/logos/logo jackpot/CCG Logos/coastal.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/desert conference.png` | `d633e0e64e988b3a09cd36f2a72f4a1ce8ff4ef4` | `Unused/logos/logo jackpot/CCG Logos/desert conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/florida conference.png` | `c2221c33e67edc49da497e145e551b651214f61d` | `Unused/logos/logo jackpot/CCG Logos/florida conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/gulf coast conference.png` | `a45660024667bd09580e1abee20a365faa107320` | `Unused/logos/logo jackpot/CCG Logos/gulf coast conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/high plains conference.png` | `34ecff20add73885c8f8afefde2e9a1178c45232` | `Unused/logos/logo jackpot/CCG Logos/high plains conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/horizon league.png` | `46efca6702538cd8f2008ddfbfd967e720ac98db` | `Unused/logos/logo jackpot/CCG Logos/horizon league.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/ivy league.png` | `ebafc80006653e2b3cb5193bf9f87b6759d03425` | `Unused/logos/logo jackpot/CCG Logos/ivy league.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/maac.png` | `f915fc38500188d2291c561f19a72d5c1895b71a` | `Unused/logos/logo jackpot/CCG Logos/maac.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/meac.png` | `fd9f0c2e5dcbc10ca15d9d7fc93d192ec1e5438f` | `Unused/logos/logo jackpot/CCG Logos/meac.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/midwest conference.png` | `ad42c222b9a2dbf028dacb96ca64b1452f3e440c` | `Unused/logos/logo jackpot/CCG Logos/midwest conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/missouri valley.png` | `f4fa9ea4c10aeeff51544c13dc987f5f62544f11` | `Unused/logos/logo jackpot/CCG Logos/missouri valley.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/mvfc.png` | `61d5c095805715fe4a96741090d5b5db144c7475` | `Unused/logos/logo jackpot/CCG Logos/mvfc.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/nec northeast conference.png` | `13c25a4b1a2b8becdee14acff0bfde4c99adf1be` | `Unused/logos/logo jackpot/CCG Logos/nec northeast conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/nec.png` | `c8c29a37644f7e7b1a7ec9d4614383e25799dbcf` | `Unused/logos/logo jackpot/CCG Logos/nec.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/ohio valley.png` | `4e62d8bd880b830340ac688a470acca4108dbec1` | `Unused/logos/logo jackpot/CCG Logos/ohio valley.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/pacific northwest conference.png` | `1731246094bd78e7444f92b92ea8c92bcc0503ba` | `Unused/logos/logo jackpot/CCG Logos/pacific northwest conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/patriot league.png` | `16e3ef1e25694dba479344d51d021bdbec599c91` | `Unused/logos/logo jackpot/CCG Logos/patriot league.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/pioneer league.png` | `52d558af7b9b3ddb279f1b915e0b8936d3b48ad9` | `Unused/logos/logo jackpot/CCG Logos/pioneer league.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/rocky mountain.png` | `7a82d79ac3cadae38fe0dba77f5a0eb659881b74` | `Unused/logos/logo jackpot/CCG Logos/rocky mountain.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/rust belt conference.png` | `ae4b6262a37bbc152b372745d6f03cc2e4e6937f` | `Unused/logos/logo jackpot/CCG Logos/rust belt conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/southern conference.png` | `5ec6e3ede32ef7c2f98e862556cdb74d2439161a` | `Unused/logos/logo jackpot/CCG Logos/southern conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/southland.png` | `5010b463b04c2e6b383bf2e8408fdb646cb16988` | `Unused/logos/logo jackpot/CCG Logos/southland.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/summit league.png` | `a8af832791a4d1f6d12614c6660f2d103ecee6b7` | `Unused/logos/logo jackpot/CCG Logos/summit league.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/sun belt.png` | `1eaf233b1bb421f76b170a61926626f84feb9f9f` | `Unused/logos/logo jackpot/CCG Logos/sun belt.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/swac.png` | `f60e931138ad8c49e5dc72677a3ed8e727f064a8` | `Unused/logos/logo jackpot/CCG Logos/swac.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/texas conference.png` | `09fc6f19b50267b1bab0b820c0500a90c2b28597` | `Unused/logos/logo jackpot/CCG Logos/texas conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/united athletic.png` | `eee65fd8040927cb81804c2ff2028024c53c6245` | `Unused/logos/logo jackpot/CCG Logos/united athletic.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/wac.png` | `b57c0889fe6c2bec5acc69af214acec738116c0d` | `Unused/logos/logo jackpot/CCG Logos/wac.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Logos/west coast.png` | `4dd69363b973ce3c5ea09cad6dd7230c34375114` | `Unused/logos/logo jackpot/CCG Logos/west coast.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/acc 1953-1978.png` | `f7ac017f2afdcdf22c9dbeca6ed0e7d7e9e972d3` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/acc 1953-1978.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/acc 1978-1987.png` | `38dd1f7efce9f87a4ee83ed738a923e2d0e47053` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/acc 1978-1987.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/acc 1987-1991.png` | `11d31fc830fd4f996d91fa44da564ed5be0890a5` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/acc 1987-1991.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/acc 1991-1997.png` | `36127044959f9b9177c2786e08a517fc6d1eafc6` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/acc 1991-1997.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/acc 1997-2005.png` | `32b0a88fe3ac4cae426e93edad950c899a211579` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/acc 1997-2005.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/acc 2005-2014.png` | `5ed3bfa0d84e9edf38adb0d100f2f33d0356e7f8` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/acc 2005-2014.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/america east 1996-2008.png` | `c21faa18da3ff26f190f1a0bd91b55fc345a5d55` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/america east 1996-2008.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/america east 2008-2013.png` | `dab2647c367345f6ee8ce06cdb0111355152a607` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/america east 2008-2013.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/america east 2013-2024.png` | `8092693fdab4397c98f27be8265be5b78a4c4d02` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/america east 2013-2024.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/american 2013-2016.png` | `44fe2559b2375bcc0b5d9bfa4b9d656f2c6b5934` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/american 2013-2016.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/american 2016-2017.png` | `a3d80a8753eae5caa4d616e75b0b6e6478f5a795` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/american 2016-2017.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/atlantic 10 1982-1995.png` | `2928a7963347117bb93afd1ad20435caef4d07c4` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/atlantic 10 1982-1995.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/atlantic 10 1995-2003.png` | `2eff41b1816dfdce26fe28719f68bed85b16aa01` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/atlantic 10 1995-2003.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/atlantic 10 2003-2014.png` | `9ad2e2684de7f4933a97821d40c67ee21ae429bc` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/atlantic 10 2003-2014.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/atlantic sun 2000-2015.png` | `a4977727dc7ec18e49b8b0b56af920f248d87d4c` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/atlantic sun 2000-2015.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/big 12 1996-2004.png` | `0a8664dadef33a0e92c679957e048cf8f6657f05` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/big 12 1996-2004.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/big 12 2003-2014.png` | `c1d7b2dbdc9a7c8ba9ec8ef7ffd85202ce5b6761` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/big 12 2003-2014.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/big 12 2014-2026.png` | `643330734d6f4d517eb6e6771ff5fac90597e952` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/big 12 2014-2026.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/big east 1979-1998.png` | `6fb68b39e399a72a423948ff1efd8c09b2fd7a7d` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/big east 1979-1998.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/big east 1998-2005.png` | `e7581b6692a42d70537129d0999197a4ae932572` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/big east 1998-2005.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/big eight.png` | `c40eddad80ae8a4b00d734d8b513bbe71d2820a1` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/big eight.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/big sky 1970-1996.png` | `c9acedb8da5b38357e26e37ff1088e99c7d81435` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/big sky 1970-1996.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/big sky 1996-2012.png` | `7fc431dc07dc26e1cc64851ece3ef2cec1285054` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/big sky 1996-2012.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/big south 1983-1998.png` | `713209af80057af3d5cc008706b1b397cef17c6d` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/big south 1983-1998.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/big south 1998-2006.png` | `c40cfa4fc58b8ac9476c987d28c776510d437d0e` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/big south 1998-2006.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/big south 2006-2012.png` | `2924aed6d069e15862601803af9c8c6505eaf854` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/big south 2006-2012.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/big south 2012-2017.png` | `89af9f4cdb2f6b7278a1c905f2bc459977b59c72` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/big south 2012-2017.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/big ten 1970-1984.png` | `6137ed40989f58d3a97dd48b2f92081fc43a6688` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/big ten 1970-1984.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/big ten 1985-1991.png` | `5e932e463a6c159d09cbe2ad8ba4dfd3ac879a45` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/big ten 1985-1991.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/big ten 1992-2011.png` | `43fbb2ffe1547395df6d8424724154a540da6e4a` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/big ten 1992-2011.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/big west 1988-1995.png` | `00072e893c51e0f72ecfcc74ef1b08641d8aaf19` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/big west 1988-1995.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/big west 1995-2005.png` | `3f90fea8cff01a7bc0306d01c513c8fe307e429e` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/big west 1995-2005.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/big west 2005-2016.png` | `816c146e9b92fa769300f7d0f965ce840671ca83` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/big west 2005-2016.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/big west 2016-2021.png` | `1c87983fbd964139c2cde2133483ccb765b7c63a` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/big west 2016-2021.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/caa 1985-2003.png` | `f9f642bea3b1a00a25fbd776e78fa94acf7722de` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/caa 1985-2003.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/caa 2003-2013.png` | `b02fa2395a93b96e603ba33c2d982cc5e84f27bd` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/caa 2003-2013.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/caa 2013-2019.png` | `6b968cab64fbfcb61fd9c9de525fe74c8311755e` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/caa 2013-2019.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/conference usa 1995-2000.png` | `aefb8b95e8d9f01daae6df2a6a370fec52d586eb` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/conference usa 1995-2000.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/conference usa 2000-2002.png` | `43336001fe5846790de40d8d6fd825001a3f005a` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/conference usa 2000-2002.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/conference usa 2003-2005.png` | `eca80d790ff18881b4d22de6c4d0dee41300c97e` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/conference usa 2003-2005.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/conference usa 2005-2012.png` | `d5b553a73e82f8ba326d508d434cf664dd8b2944` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/conference usa 2005-2012.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/conference usa 2013-2022.png` | `9c460484735ba645fb3254785fe64c32f9c867f8` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/conference usa 2013-2022.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/conference usa 2023.png` | `2a39e861c4917d2ea5a48de1e5d49cde9dd1771a` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/conference usa 2023.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/east coast conference shield.png` | `181fd5b5add804f3d278603c32c8b9e74acd85a6` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/east coast conference shield.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/east coast conference.png` | `eac610c911b77ae16338aa1ed63278e1027dbeb4` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/east coast conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/great west.png` | `9e6f1a735dd41fbe4ad18a3d44b33382f1197769` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/great west.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/horizon league 2001-2014.png` | `165506c7b8b2da2616aee183be48f432f49ccb5e` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/horizon league 2001-2014.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/horizon league 2014-2023.png` | `22e9ae3122200ed5071689c32cba691ab792d7c0` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/horizon league 2014-2023.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/ivy league 1982-2019.png` | `c18e1c2890de04a0236e336df2544598558799df` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/ivy league 1982-2019.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/maac 1980-1983.png` | `40706ebb6b43b24129d0d9157ab05713ea181fed` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/maac 1980-1983.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/maac 1983-1987.png` | `206f5ec298f8ebcb92ea170630f2bda5fe8f16d2` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/maac 1983-1987.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/maac 1987-1995.png` | `f66d502400732eabb5a4c84c979c58fdbfe4cccb` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/maac 1987-1995.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/maac 1995-2003.png` | `9edee725a46b42a4bfe0cb832d737e7de579ef47` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/maac 1995-2003.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/maac 2003-2023.png` | `4b116742907880e943c3ce3fd32acad1cbb64921` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/maac 2003-2023.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/mac 1946-1987.png` | `ec1ef9444af03804a37507c552c646360f916bd0` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/mac 1946-1987.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/mac 1987-2001.png` | `6260d8592bca81ae7e8f13e544241ff923b545bf` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/mac 1987-2001.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/mac 2001-2008.png` | `b1537d537d66968dd554fa70033d7a0ebd299a94` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/mac 2001-2008.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/meac 1970-2004.png` | `f56f3b44b11ff708d6ae7ea3d82c7b0cc6863c72` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/meac 1970-2004.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/meac 2004-2012.png` | `0565cc28f44d7d115640a0d1cc46e01f80f501cb` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/meac 2004-2012.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/meac 2012-2018.png` | `770641aa295de2c4c6919d725eaab5e09b910d88` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/meac 2012-2018.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/metro conference.png` | `529a0275c35811989f164ef0b0f32f3cbc35bd0f` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/metro conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/mid continent.png` | `9ed46b4ad0da5c11a5a277200fcd52099fbe94dd` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/mid continent.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/missouri valley 1907-1948.png` | `b5c25f2702ccac60014cfd118805039eadde49ef` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/missouri valley 1907-1948.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/missouri valley 1948-1966.png` | `0e1e8ec7625f8486877372a1e2ddbf27e5612793` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/missouri valley 1948-1966.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/missouri valley 1966-1970.png` | `2e7a06a0da55bdbd9a0322692f19a331d488c0e3` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/missouri valley 1966-1970.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/missouri valley 1970-1975.png` | `308bb0ad56154262f670088ae3133953af71c3c0` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/missouri valley 1970-1975.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/missouri valley 1975-1988.png` | `df35e7d94d6d1828f53d20b863f043dd061b559e` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/missouri valley 1975-1988.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/missouri valley mvc.png` | `7beba64b1c7d62e93979eaac6d4f542a62731df7` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/missouri valley mvc.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/mountain west 1999-2011.png` | `ea40306ad899ceb35fdf0b4cc2e39812789f3d72` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/mountain west 1999-2011.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/ohio valley 1948-1966.png` | `4d2d849d0fcb0416fe207d063592aed4557d9474` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/ohio valley 1948-1966.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/ohio valley 1966-1975.png` | `2931ee5d19a15fcbac61116eafbd344045ee9ba6` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/ohio valley 1966-1975.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/ohio valley 1975-1979.png` | `4b37f4acbac6fb2a6a6069b398298026c5628018` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/ohio valley 1975-1979.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/ohio valley 1979-1993.png` | `f3267892fd2138c005ca566b92aabd0a76558649` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/ohio valley 1979-1993.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/ohio valley 1993-2002.png` | `f5f45a53b8885c5598739753e8e36c5415ba9233` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/ohio valley 1993-2002.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/pac-10 1978-1994.png` | `77fecde8ec6b38283c6a329f89871e45b0841ae4` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/pac-10 1978-1994.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/pac-10 1995-2009.png` | `0419d6a00d77b7b88bf4c8b477d44ce0b5bbac6f` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/pac-10 1995-2009.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/pac-10 2010-2011.png` | `5706629b96a1efb46a876afc69ddbcdd45c2c4d4` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/pac-10 2010-2011.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/pac-12 2010-2026.png` | `c9e06e04d3d6edebcf7d90e06946c8ec7f4afe95` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/pac-12 2010-2026.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/pac-12 circle.png` | `cb58135b03efa861c0283cd62f4df7f8ee0a6f6e` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/pac-12 circle.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/pac-8.png` | `506d38d6f93c7987b8a4cd2851122a107523934d` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/pac-8.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/pacific coast.png` | `03dfd94f705522e83a6b8815949c9ecf9be038f7` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/pacific coast.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/sec 1932-1964.png` | `b4f4dc60e072234e5e8bb854c8fae94236a64710` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/sec 1932-1964.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/sec 1964-1966.png` | `137b61fa967c2084a5379ce55bef6138d3f81161` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/sec 1964-1966.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/sec 1966-1970.png` | `1cf2ac64f9393d45303da009cd0991324de8d0cc` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/sec 1966-1970.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/sec 1970-1988.png` | `e505fd2433b1619b49cfe24bdc0d9317cdd05c5d` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/sec 1970-1988.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/sec 1988-2008.png` | `b30cbfb18eaec371e78301ac39e643a2017f2049` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/sec 1988-2008.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/sec 2008-2022.png` | `3674ff668532bf1d460ce71ae5c6d6fa5b69bdd8` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/sec 2008-2022.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/southern 1958-1964.png` | `46651f6604939a9da28c68d7033f1d1ff91f8e3a` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/southern 1958-1964.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/southern 1964-1999.png` | `d605044b3fc829f65a23f616cecf76c2dbdbc0a2` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/southern 1964-1999.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/southern 1999-2023.png` | `fe469a377f5333e74dc8ee76cf1ba0a57d7b21cb` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/southern 1999-2023.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/southland 1963-1972.png` | `7f5cce6610981179710ae69a1412313764e0f8b0` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/southland 1963-1972.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/southland 1972-2002.png` | `9dbdd208f6d7fdaf82554317211964be5829293b` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/southland 1972-2002.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/southland 2002-2012.png` | `ccaf50cff93f1a371f473bd14a7134f89600230d` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/southland 2002-2012.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/southland 2012-2023.png` | `9a1e3470249878f68442ee9b71400effd1ebd0f2` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/southland 2012-2023.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/sun belt 1976-1980.png` | `af9cdf5b4f9a8239a83c081fd78f2cd25d4691be` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/sun belt 1976-1980.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/sun belt 1980-1982.png` | `c7693f13e97b5edb7d155113749aedfa343ab362` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/sun belt 1980-1982.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/sun belt 1982-1991.png` | `7af566cef566db98e8a750571e0c61730d36ed56` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/sun belt 1982-1991.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/sun belt 1991-1997.png` | `2691b174ab570d65396b3651495db7040dfcbaca` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/sun belt 1991-1997.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/sun belt 1997-2013.png` | `f5f3d1954b6fc0c6a4db1e45b74f863175c3c6e5` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/sun belt 1997-2013.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/swac 1979-1982.png` | `8726c3faba05141552db0e4d4d0db0aad11c1247` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/swac 1979-1982.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/swac 1982-2001.png` | `e35e7ff147770333306d9f4c1a79188849149da4` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/swac 1982-2001.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/swac 2001-2020.png` | `a1e4d3716285342c7772557dc8f08d49db2e4d14` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/swac 2001-2020.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/swc.png` | `0300c44fba6bf352c27aa38410dda9379180ae4b` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/swc.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/wac 1962-1982.png` | `34f907e83f63e5c7290be6a4d1659927a8126ac4` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/wac 1962-1982.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/wac 1982-1992.png` | `d2d8d2e81b4a8ecc15d264794c9f70e44abd55e7` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/wac 1982-1992.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/wac 1992-2005.png` | `19a7c15e9d80889c2abaa15c3e7197d3b6b3ca7d` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/wac 1992-2005.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/west coast 1972-1989.png` | `9fb4e248428f36d362224ec25d68f963c9bdb215` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/west coast 1972-1989.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/west coast 1989-1995.png` | `ca3ea87e27195603927a1bfd0fe74ecae9375283` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/west coast 1989-1995.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/west coast 1995-2011.png` | `923d2249abfa5dae4ec0892e992ffcb411157879` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/west coast 1995-2011.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/Throwbacks/west coast 2011-2019.png` | `c00293f37a2e4baf1ddaacad27d52ece3de18a0e` | `Unused/logos/logo jackpot/CCG Stickers/Throwbacks/west coast 2011-2019.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/america east.png` | `09695d91c5d668f2508d8a91de6e3571fa6a3e6c` | `Unused/logos/logo jackpot/CCG Stickers/america east.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/appalachian conference.png` | `a5f14416111d1d2300d9ebf8621b93cdc6b6ae62` | `Unused/logos/logo jackpot/CCG Stickers/appalachian conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/asun.png` | `418410968c9e7c285211133212caa117e4920898` | `Unused/logos/logo jackpot/CCG Stickers/asun.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/atlantic 10.png` | `1a82b3639569a0a12ad43eebdadd98b29fd0224c` | `Unused/logos/logo jackpot/CCG Stickers/atlantic 10.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/big east.png` | `11bb65f223913ba1fee319387d10cb97b6b85c1a` | `Unused/logos/logo jackpot/CCG Stickers/big east.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/big sky.png` | `07b4c8e3255d19695f8565a03f49ec57622536b3` | `Unused/logos/logo jackpot/CCG Stickers/big sky.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/big south.png` | `80b99b5c19d41af30471a82641a63ea939f268fa` | `Unused/logos/logo jackpot/CCG Stickers/big south.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/big west.png` | `f679379d7a852536b1c155cb9b6f61684ffbe0f5` | `Unused/logos/logo jackpot/CCG Stickers/big west.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/caa football.png` | `694e2557aab887166c80d9d97841b699700dc236` | `Unused/logos/logo jackpot/CCG Stickers/caa football.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/california conference.png` | `4026f141d61e57938013e869cac7778bc6bdc49b` | `Unused/logos/logo jackpot/CCG Stickers/california conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/chesapeake conference.png` | `01c3d936716c67d8789972c9384e52b1890f14fa` | `Unused/logos/logo jackpot/CCG Stickers/chesapeake conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/coastal.png` | `60e505fd1eef66335132dd2417e60c2cbb5b80c9` | `Unused/logos/logo jackpot/CCG Stickers/coastal.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/desert conference.png` | `1bc07bfe58bdd561e97fe34d3979f93ffcb0e617` | `Unused/logos/logo jackpot/CCG Stickers/desert conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/florida conference.png` | `2b051b42158b7b6756c86404993bae634b788bff` | `Unused/logos/logo jackpot/CCG Stickers/florida conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/gulf coast conference.png` | `7f876787db3e159d3583253c0fb788fe19719c8a` | `Unused/logos/logo jackpot/CCG Stickers/gulf coast conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/high plains conference.png` | `f34bad832de763a1c0051360fb108423312775ca` | `Unused/logos/logo jackpot/CCG Stickers/high plains conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/horizon league.png` | `dc05d796dc871c506b821ac82b76b6fac149cab0` | `Unused/logos/logo jackpot/CCG Stickers/horizon league.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/ivy league.png` | `b383608cf1bcdfef1a8050d62d963949eb8ff08c` | `Unused/logos/logo jackpot/CCG Stickers/ivy league.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/maac.png` | `bf72577fe8bbe32d006c892a5693e01ec6eda9c1` | `Unused/logos/logo jackpot/CCG Stickers/maac.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/meac.png` | `ec54961c386e30222b0ab7b520ce6d4eb0c794f7` | `Unused/logos/logo jackpot/CCG Stickers/meac.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/midwest conference.png` | `648ab01b764b2108f6b08f9bf89d62f6a0499072` | `Unused/logos/logo jackpot/CCG Stickers/midwest conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/missouri valley.png` | `c63c9e285634301612158f58c95c915cb80160cf` | `Unused/logos/logo jackpot/CCG Stickers/missouri valley.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/mvfc.png` | `e69824266ff6d683513c186ca68632215f3f6063` | `Unused/logos/logo jackpot/CCG Stickers/mvfc.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/nec northeast conference.png` | `568ce2190836f84960697891bcd016c2400f4222` | `Unused/logos/logo jackpot/CCG Stickers/nec northeast conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/nec.png` | `df39b252a9379b34bf725d331335b18124fd8fa0` | `Unused/logos/logo jackpot/CCG Stickers/nec.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/ohio valley.png` | `f2d968a54857d2bbf0848f45e9736fe55c690422` | `Unused/logos/logo jackpot/CCG Stickers/ohio valley.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/pacific northwest conference.png` | `98c8157ce547377cce28705718f22b7a15aa8571` | `Unused/logos/logo jackpot/CCG Stickers/pacific northwest conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/patriot league.png` | `6abd8fa0f59d952cc0f064b1c96684a0b933f040` | `Unused/logos/logo jackpot/CCG Stickers/patriot league.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/pioneer league.png` | `f3811ce337fd688cf10a70325c08a0a73c781a75` | `Unused/logos/logo jackpot/CCG Stickers/pioneer league.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/rocky mountain.png` | `719bfecc344669039f3941d5c6cf524df40db2d6` | `Unused/logos/logo jackpot/CCG Stickers/rocky mountain.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/rust belt conference.png` | `0f91d87d6e784cfc195bfc5185b96cc4979dcbf4` | `Unused/logos/logo jackpot/CCG Stickers/rust belt conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/southern conference.png` | `30ea0e2615b37987cc0c1a837b35b9028c0e052b` | `Unused/logos/logo jackpot/CCG Stickers/southern conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/southland.png` | `8797880a3e75e6d5279765b0280f147c4e86d36e` | `Unused/logos/logo jackpot/CCG Stickers/southland.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/summit league.png` | `610f97dbe7dbf69500982a25974227605134280c` | `Unused/logos/logo jackpot/CCG Stickers/summit league.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/sun belt.png` | `4085d6ae8b44a81db609d6e19e6cf339a5775c7b` | `Unused/logos/logo jackpot/CCG Stickers/sun belt.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/swac.png` | `73e5d93cfa4f972dab73e3b18c9bb0a7b3363485` | `Unused/logos/logo jackpot/CCG Stickers/swac.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/texas conference.png` | `ad821742babe9eb5f177c313c6640c5f6716c503` | `Unused/logos/logo jackpot/CCG Stickers/texas conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/united athletic.png` | `91c95eda947a658e6d31d2edce2646f4bf34c404` | `Unused/logos/logo jackpot/CCG Stickers/united athletic.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/wac.png` | `cf2b13a49a2a34db5cec46a643c2d8dfafccd571` | `Unused/logos/logo jackpot/CCG Stickers/wac.png` | Identical Git blob |
| `assets/logos/logo jackpot/CCG Stickers/west coast.png` | `dbcd0330355fa7decfbcbb48a54fc9ca33e08a6a` | `Unused/logos/logo jackpot/CCG Stickers/west coast.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/acc 1953-1978.png` | `4d97251d82e6775698caf4c93d574b3a510ff967` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/acc 1953-1978.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/acc 1978-1987.png` | `8609a01385f7b543cd224af249f84748053be4c0` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/acc 1978-1987.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/acc 1987-1991.png` | `599afd5fb829cfc427de3b55def2336a76ea1bdc` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/acc 1987-1991.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/acc 1991-1997.png` | `fc8ff0cb5f4dae438945a0bd15c7232ea6a874ad` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/acc 1991-1997.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/acc 1997-2005.png` | `d2fd5e655dac6e7b43bac85746394d80a8d9c15d` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/acc 1997-2005.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/acc 2005-2014.png` | `132b2e6b608a41c97eaafef9f23d617f75d2a092` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/acc 2005-2014.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/america east 1996-2008.png` | `a231e8c883c2eb0379076d2711b12a9f9c41154d` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/america east 1996-2008.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/america east 2008-2013.png` | `746bb5e7c765212ff51e0af2e1a45e84a2f31045` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/america east 2008-2013.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/america east 2013-2024.png` | `d7f4b5604cc008f5a9bfc8f2b19ccddc418866a3` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/america east 2013-2024.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/american 2013-2016.png` | `d6344db4206af966dcdfea3b45d637180b17d2be` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/american 2013-2016.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/american 2016-2017.png` | `da867b021e0f5d749a29af272d30e65c824aeca1` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/american 2016-2017.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/atlantic 10 1982-1995.png` | `8f6642d29653338e1d050a805cf255d916bb17c7` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/atlantic 10 1982-1995.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/atlantic 10 1995-2003.png` | `aec8c45254e30e98566efc850428c6173e7e7229` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/atlantic 10 1995-2003.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/atlantic 10 2003-2014.png` | `c595d8e7ea53003119aaf41d96a53fb5fd9d0530` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/atlantic 10 2003-2014.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/atlantic sun 2000-2015.png` | `873e7fe4d916caa77c67954248bf2fbf8ef6f931` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/atlantic sun 2000-2015.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/big 12 1996-2004.png` | `2f650a3edc4c36625cf719861d096a3ba94a4d90` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/big 12 1996-2004.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/big east 1979-1998.png` | `13aaa638573792b0bcae7fe7df17f402478bc753` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/big east 1979-1998.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/big east 1998-2005.png` | `1839cb95c27be7dd9e7323d073f431a41b8d409d` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/big east 1998-2005.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/big sky 1970-1996.png` | `7010589381e0099395d2ba70c8b264eb15fc3386` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/big sky 1970-1996.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/big sky 1996-2012.png` | `3df468547678bff7bdb9f7c2d7d23867ac6a82d8` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/big sky 1996-2012.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/big south 1983-1998.png` | `2937d65848f3251898ff49be0f9e8eae919e933c` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/big south 1983-1998.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/big south 1998-2006.png` | `fb83cab4579ce5c9d2475f4c19f8950e5b683922` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/big south 1998-2006.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/big south 2006-2012.png` | `2cc3ddbc9df1d2ad1574776e5a4d61c7a8500d56` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/big south 2006-2012.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/big south 2012-2017.png` | `29ad9c6283b01389d634e0acd6bbfc619f729f74` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/big south 2012-2017.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/big west 1988-1995.png` | `a36df5249e966877bd193097cf0de0bfeed33a2d` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/big west 1988-1995.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/big west 1995-2005.png` | `0ca1122d3c62b1c1dd33b27ffaaa6a45905fb45f` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/big west 1995-2005.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/big west 2005-2016.png` | `095f7921b1861c130c403d2aa38a14f8b1251ed8` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/big west 2005-2016.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/big west 2016-2021.png` | `48daa1c01cb0c016801cc8bd5ff473e29fbe7d13` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/big west 2016-2021.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/caa 1985-2003.png` | `a703ebedd8b3cec7e638a1a1efb17b0b023f2ba2` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/caa 1985-2003.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/caa 2003-2013.png` | `fc71b98e36b33cce03fb6aa86a4ca5fde99c2dce` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/caa 2003-2013.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/caa 2013-2019.png` | `a26ca1cb830f179a150c25685058b471a9c72678` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/caa 2013-2019.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/conference usa 2000-2002.png` | `12c6e69344a6e64c9ff44fc58e1dacbf01106940` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/conference usa 2000-2002.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/east coast conference shield.png` | `7299479fd2aeae591f5efedc420cd1924356c1ea` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/east coast conference shield.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/east coast conference.png` | `430cb17e6d6172ccd05f2a4f9080de554df3e0e9` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/east coast conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/great west.png` | `b66c63d68fd2bed49dfbadbe762d93bf8a38e214` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/great west.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/horizon league 2001-2014.png` | `f59cb94703104b8b34d7cca265715fc509a663f4` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/horizon league 2001-2014.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/horizon league 2014-2023.png` | `a86f9a6cd2b344a622ba4b69f98c5230841fb549` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/horizon league 2014-2023.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/ivy league 1982-2019.png` | `8bbbbc00121b2008b563e3285e6a3c7bc82b8c1a` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/ivy league 1982-2019.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/maac 1980-1983.png` | `5f476d038d5ac02e837d58b1df9277ae2aad98bf` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/maac 1980-1983.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/maac 1983-1987.png` | `fab0ef65ab65ca7035bd14f02d9063d89543e5de` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/maac 1983-1987.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/maac 1987-1995.png` | `89c6e221b636ee916fd8c28f16d73c3211d20b3d` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/maac 1987-1995.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/maac 1995-2003.png` | `651905a50c4e2246c9ee4cde0ef625271e8a0d03` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/maac 1995-2003.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/maac 2003-2023.png` | `bfc7f9f0ad71bda1f4741713a8a3ae7c24394ad4` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/maac 2003-2023.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/mac 1946-1987.png` | `7d2311542a4647dd153287a375dbb5b690d9ca5e` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/mac 1946-1987.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/mac 1987-2001.png` | `10833be5be28c4155d20ce11a4abde0dc71fa72a` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/mac 1987-2001.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/mac 2001-2008.png` | `9742100edcf6f663d80e5893ac727113ae4f8a63` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/mac 2001-2008.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/meac 1970-2004.png` | `bc110f56270e432e270d8b7acbb2c25d8d45f789` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/meac 1970-2004.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/meac 2004-2012.png` | `4b75e2a1a77d6bf4a09b33073bd1ca86812bcb5a` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/meac 2004-2012.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/meac 2012-2018.png` | `d42f65fb9342575ee342a8abdc0f6d8d4f466592` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/meac 2012-2018.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/metro conference.png` | `263d83cdac51393fdcaa1e0a9e29a7cbb8912be2` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/metro conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/mid continent.png` | `1168ef9f722f8b50e0a181568284f71c01758791` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/mid continent.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/missouri valley 1907-1948.png` | `c4d3a908edb39485e69e372ce906923a2af146e4` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/missouri valley 1907-1948.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/missouri valley 1948-1966.png` | `2794bd8349c7715cc17cfca289d1271331d80955` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/missouri valley 1948-1966.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/missouri valley 1966-1970.png` | `dde1aeeae10c6ceef3a46cf705b96b0fa9bff958` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/missouri valley 1966-1970.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/missouri valley 1970-1975.png` | `e352a6c1362f5df1380019bf19d0b5d2018c77e7` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/missouri valley 1970-1975.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/missouri valley 1975-1988.png` | `6db073cfe543f3c967a8bcb66537f9ab571e7717` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/missouri valley 1975-1988.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/missouri valley mvc.png` | `2d28ae69fd07dfe32aaa388d7d60e746e9029a97` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/missouri valley mvc.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/mountain west 1999-2011.png` | `8063e2dfd0fabddda9d67632edc0bb376e59b777` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/mountain west 1999-2011.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/ohio valley 1948-1966.png` | `bb95cac1df672fa0d75063944177bc165b72c2db` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/ohio valley 1948-1966.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/ohio valley 1966-1975.png` | `0c0d38beb8eaa8960bc70e20e9a40a7a7b2151b2` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/ohio valley 1966-1975.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/ohio valley 1975-1979.png` | `26311b36d9257222bc2e915c0fbf496dc656a99e` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/ohio valley 1975-1979.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/ohio valley 1979-1993.png` | `fe6d1ab7017d9c40c80bb4e603b44d710ddb449a` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/ohio valley 1979-1993.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/ohio valley 1993-2002.png` | `31dbca04fb150532ed67224441639b460a4a3164` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/ohio valley 1993-2002.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/pac-10 2010-2011.png` | `47e0ccc66a225559d5a63f846e86823710a6bf0e` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/pac-10 2010-2011.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/sec 1964-1966.png` | `07d84c71c034add769e974016b19a8ebc182911c` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/sec 1964-1966.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/southern 1958-1964.png` | `b1d75cf9d118c2bb095d84a9e73f38dc241142c8` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/southern 1958-1964.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/southern 1964-1999.png` | `d09a1c567d27daec0a2d100b24e91fbf5f814e96` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/southern 1964-1999.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/southern 1999-2023.png` | `f2ac88f5905b2cf76e4a79fa4300b3a9e597577e` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/southern 1999-2023.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/southland 1963-1972.png` | `8b3428b5618395e9b403dffe10e51a9226db88b9` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/southland 1963-1972.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/southland 1972-2002.png` | `a6b9c141bd21bda94f42d6cd4b57a9af578cffeb` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/southland 1972-2002.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/southland 2002-2012.png` | `0ccf3489c53b9a18d9df4d4e89191bf80e2f6f45` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/southland 2002-2012.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/southland 2012-2023.png` | `f650650c01f7a7d1e724d82da5998b1f4ed15329` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/southland 2012-2023.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/sun belt 1976-1980.png` | `1f8795a58a96ebf852e3b177fda444fa970c7fb4` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/sun belt 1976-1980.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/sun belt 1980-1982.png` | `5f24a19479ffff5d84452746630184dd1d7a04bf` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/sun belt 1980-1982.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/sun belt 1982-1991.png` | `0e96f7771803f825b43dede5a3f2d7d88694eacc` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/sun belt 1982-1991.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/sun belt 1991-1997.png` | `ca8f9da42409fe02d046c82e2c8c218f0c8bb704` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/sun belt 1991-1997.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/sun belt 1997-2013.png` | `7b810c27bf0dd6052947bbcd44b5c9f25810c2e3` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/sun belt 1997-2013.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/sun belt 2013-2020.png` | `d86fe7890f367826a7f27d3cb9164feb263a7ee0` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/sun belt 2013-2020.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/swac 1979-1982.png` | `cca2b68c1de4d4f4d87f6b50fec62e45034293de` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/swac 1979-1982.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/swac 1982-2001.png` | `c54e2b4ae15e22e8b7de88493baeffa9ccefec8c` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/swac 1982-2001.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/swac 2001-2020.png` | `70153590aa494916785a6134638eddc3eea2d08c` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/swac 2001-2020.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/wac 1962-1982.png` | `d7e392b41dc6d6052626589f746dc774d1d9c188` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/wac 1962-1982.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/wac 1982-1992.png` | `852d78d74e80001c3a154da3e92295ba4b2da53b` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/wac 1982-1992.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/wac 1992-2005.png` | `69378448aba0e3cac620e3843a610f717ea159d1` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/wac 1992-2005.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/west coast 1972-1989.png` | `f873997a812aa3ce6fad08a2440c83df4d781fa6` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/west coast 1972-1989.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/west coast 1989-1995.png` | `c9f3d2e84cb9dba03e26a6d33e49f8fd49578034` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/west coast 1989-1995.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/west coast 1995-2011.png` | `ae2207d6e28c1bccc2ed4be01b0407b6f2abe473` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/west coast 1995-2011.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/Throwbacks/west coast 2011-2019.png` | `3dc306d33b2fd322ae51303bc77d0a6c0792af44` | `Unused/logos/logo jackpot/Con Logos/Throwbacks/west coast 2011-2019.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/america east.png` | `312d547ac87d934339aab4150eb500d3f0c7cafd` | `Unused/logos/logo jackpot/Con Logos/america east.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/appalachian conference.png` | `fdd62a2a810952606c655cbb03547c0912fd23bb` | `Unused/logos/logo jackpot/Con Logos/appalachian conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/asun.png` | `1bc857e55c0232e00662256a773f5f53faf865fa` | `Unused/logos/logo jackpot/Con Logos/asun.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/atlantic 10.png` | `269013c11dd67d15ce0657636fa1ba8d556322a9` | `Unused/logos/logo jackpot/Con Logos/atlantic 10.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/big sky.png` | `131d78fa271e08a898ac3dbc6487d8eef16c2534` | `Unused/logos/logo jackpot/Con Logos/big sky.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/big south.png` | `a6b8868714e52a7bfaf9e0211b9e2534f46135cc` | `Unused/logos/logo jackpot/Con Logos/big south.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/caa football.png` | `4c94d24710bcf4c6cb73e93973851d5f7719f6cf` | `Unused/logos/logo jackpot/Con Logos/caa football.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/california conference.png` | `22b633b50268b7cc736f5f0abd0b02eee3513ce2` | `Unused/logos/logo jackpot/Con Logos/california conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/chesapeake conference.png` | `628f8ddd189a807f84865bee8d19a14c6c6e070e` | `Unused/logos/logo jackpot/Con Logos/chesapeake conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/coastal.png` | `72fa49de9e8e21762a15cb3899ef81cec74fa5d7` | `Unused/logos/logo jackpot/Con Logos/coastal.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/desert conference.png` | `0ea713fb807e061c4fa6f2e65e933d1974123092` | `Unused/logos/logo jackpot/Con Logos/desert conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/div 1 independents.png` | `99543a0b504a117368e3da9c24405daf0d58f57e` | `Unused/logos/logo jackpot/Con Logos/div 1 independents.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/florida conference.png` | `f762ab8dcd51fa1fb2ef3f328fec9860745b1ab7` | `Unused/logos/logo jackpot/Con Logos/florida conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/gulf coast conference.png` | `93156fd10a372c7e56701c9b489585d8a3dae364` | `Unused/logos/logo jackpot/Con Logos/gulf coast conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/high plains conference.png` | `4be33c936ce20e72ecd7d870aa5ed34c9605522d` | `Unused/logos/logo jackpot/Con Logos/high plains conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/horizon league.png` | `2cdf0948146f9c8237516d3cf84facae7061fccd` | `Unused/logos/logo jackpot/Con Logos/horizon league.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/ivy league.png` | `93e81cc0b7859ec94eaef5769988938f530200e3` | `Unused/logos/logo jackpot/Con Logos/ivy league.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/maac.png` | `8ff1716f5c10e2e384738c732d3a2b80180c8aab` | `Unused/logos/logo jackpot/Con Logos/maac.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/meac.png` | `c51de22aa4462d1f23d70798dfcc21e49d6ed76d` | `Unused/logos/logo jackpot/Con Logos/meac.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/midwest conference.png` | `c6ad716766451b8f48022dfd3a751794801a3263` | `Unused/logos/logo jackpot/Con Logos/midwest conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/missouri valley.png` | `b1b1f782179e89e7af99c4bd06996c74047dc392` | `Unused/logos/logo jackpot/Con Logos/missouri valley.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/mvfc.png` | `b1866bc7497e3be4f9277ef48556cd486e7794bf` | `Unused/logos/logo jackpot/Con Logos/mvfc.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/nec northeast conference.png` | `af32b5cd7629fd2bfb0aa7ab22fb6e31f6c4e381` | `Unused/logos/logo jackpot/Con Logos/nec northeast conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/nec.png` | `dd835553e8841c491291463300db93745f798832` | `Unused/logos/logo jackpot/Con Logos/nec.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/ohio valley.png` | `16799cca198a48ef16d19b087252ac9f3e1760b2` | `Unused/logos/logo jackpot/Con Logos/ohio valley.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/pacific northwest conference.png` | `ccdf5980c90387ba80a7f16aa81ea9ccd5e687e0` | `Unused/logos/logo jackpot/Con Logos/pacific northwest conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/patriot league.png` | `6d6e4a63170464ef57dc6dea1af282a91c42cc42` | `Unused/logos/logo jackpot/Con Logos/patriot league.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/pioneer league.png` | `9027cfa3e155dcae9d91c1a359eea06945f9048d` | `Unused/logos/logo jackpot/Con Logos/pioneer league.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/rocky mountain.png` | `db44e393203cec2dba12f5f3078f2b9d32a42abe` | `Unused/logos/logo jackpot/Con Logos/rocky mountain.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/rust belt conference.png` | `3a3ab990652785e755d6051558500ccbf721004d` | `Unused/logos/logo jackpot/Con Logos/rust belt conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/southern conference.png` | `d6ee1e9c5c168510a8dace4ad5f7ef9d175bee76` | `Unused/logos/logo jackpot/Con Logos/southern conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/southland.png` | `abf474e4cb79c7fdb6cf1ec36028b808c90dd77c` | `Unused/logos/logo jackpot/Con Logos/southland.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/swac.png` | `bc34a462cee89c245109ea6e9701d13aa06b4298` | `Unused/logos/logo jackpot/Con Logos/swac.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/texas conference.png` | `cd01749877c499e2a8f6f52874c94f6696f43adc` | `Unused/logos/logo jackpot/Con Logos/texas conference.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/united athletic.png` | `80f3bc27fa5a98ac5dc4036f5d8b05bc7f8221b9` | `Unused/logos/logo jackpot/Con Logos/united athletic.png` | Identical Git blob |
| `assets/logos/logo jackpot/Con Logos/west coast.png` | `fc6f0429aa96e8236d98e7d0bb32bc36f9e8c368` | `Unused/logos/logo jackpot/Con Logos/west coast.png` | Identical Git blob |
| `assets/logos/logo jackpot/Context` | `6358a8b506ad427c6ac65cfd47f40ad819489ed3` | `Unused/logos/logo jackpot/Context` | Identical Git blob |
| `assets/logos/source/Bowls/Alamo Bowl.png` | `a9ce8fa09ce08e6fdcf74d8a6057e8175082f6fb` | `Master/logos/Bowls/Alamo Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Aloha Bowl.png` | `d82e4411a800c7a1976aa81ee22c6276f11d51df` | `Master/logos/Bowls/Aloha Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Arizona Bowl.png` | `4cf2868bb9f3125a86ff0f10aef0a3567fb7dda3` | `Master/logos/Bowls/Arizona Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Armed Forces Bowl.png` | `01281b4f93ccc5033092826e908394c930c77bf7` | `Master/logos/Bowls/Armed Forces Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Bacardi Bowl.png` | `c45ec945a22bc3f999da9e1fa6ff4d8980eca139` | `Master/logos/Bowls/Bacardi Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Bahamas Bowl.png` | `2b1db416e01f3bad2cec6851de2b8bbb859f77c4` | `Master/logos/Bowls/Bahamas Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Birmingham Bowl.png` | `64d8f0f9772c1fd1e1cb6242ae6b89d8a160462f` | `Master/logos/Bowls/Birmingham Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Bluebonnet Bowl.png` | `157a4f1a50869af19f847c67b002a8c4931fac36` | `Master/logos/Bowls/Bluebonnet Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Boca Raton Bowl.png` | `4cc214ca9d6aade4b4149e931c7b4e343f514571` | `Master/logos/Bowls/Boca Raton Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Brooklyn Bowl.png` | `f68bfceaa63efeae4384a786910f1d22470250e5` | `Master/logos/Bowls/Brooklyn Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Camellia Bowl.png` | `0c612959817122eaec7d8373c1f302a23fc3e8fd` | `Master/logos/Bowls/Camellia Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Celebration Bowl.png` | `0318de26c0b82ebd670cfef5791d04df096d9eab` | `Master/logos/Bowls/Celebration Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Citrus Bowl.png` | `9cbefa3977be90d7d9e4b0feae09ef6736fb67d4` | `Master/logos/Bowls/Citrus Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Copper Bowl.png` | `a7e8476f25f43c44c71efca39d99ece9ba7b44cc` | `Master/logos/Bowls/Copper Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Cure Bowl.png` | `140745e9397742dac5baa418aa7bd1759c37ec53` | `Master/logos/Bowls/Cure Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Duke's Mayonnaise Bowl.png` | `83cb7ab7de08f9b3c591e364be38d1e45ef0f39c` | `Master/logos/Bowls/Duke's Mayonnaise Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/EA Sports Bowl.png` | `0f1a33eaec318783587b43bc761e3d7e7de766ed` | `Master/logos/Bowls/EA Sports Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Fenway Bowl.png` | `136343fe124e1793cb6d1f5a70fea657bfa473be` | `Master/logos/Bowls/Fenway Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Freedom Bowl.png` | `34fd15d0c566188d20004c74b87ff29ab94dea55` | `Master/logos/Bowls/Freedom Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Gasparilla Bowl.png` | `7d50bd20613aeca8935208bd3541d5f95dbd24ff` | `Master/logos/Bowls/Gasparilla Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Gator Bowl.png` | `d13eb87b55d97f1841625254611a57d9b69a92b0` | `Master/logos/Bowls/Gator Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Gotham Bowl.png` | `d51d51117a7c7aaec7c193a2d383df66d13b6d60` | `Master/logos/Bowls/Gotham Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Heritage Bowl.png` | `c5be0cc358f94753d14396696756bc0ae2d03d8c` | `Master/logos/Bowls/Heritage Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Holiday Bowl.png` | `5358eb9eec574f49d2b43b637dbf36ad30f15855` | `Master/logos/Bowls/Holiday Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Ice Bowl.png` | `81726bcd02f46365282214c6543f2eb916856ed7` | `Master/logos/Bowls/Ice Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Idaho Potato Bowl.png` | `7a15588c380ea086982b6ecd815a02862054c2c8` | `Master/logos/Bowls/Idaho Potato Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Independence Bowl.png` | `a62c1f6229c892b17caa413dfb3ef20de5c2f651` | `Master/logos/Bowls/Independence Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/International Bowl.png` | `f044e149d239919bb7d4adbd1e9cb1a43a062377` | `Master/logos/Bowls/International Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Las Vegas Bowl.png` | `0a00c05d5d4dcc8b84f3f570bc443fc9c19a1b4e` | `Master/logos/Bowls/Las Vegas Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Liberty Bowl.png` | `56fb946658fa451a45a2ece898eac76392902239` | `Master/logos/Bowls/Liberty Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Military Bowl.png` | `1fa4d1cde78af3b5845937af0b69b3c4d333016c` | `Master/logos/Bowls/Military Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Mirage Bowl.png` | `9d9a8c84c52dd97df8d73757273c27b74ffef390` | `Master/logos/Bowls/Mirage Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Motor City Bowl.png` | `629c01fec8f4a044e1256821c8ed2e2493004830` | `Master/logos/Bowls/Motor City Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Music City Bowl.png` | `8080e17aa7c94dd13b4614cb06b6379a2b58395a` | `Master/logos/Bowls/Music City Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/New Mexico Bowl.png` | `9cc805ee8e304a61ad64f323ca70a9fcd8e22cf0` | `Master/logos/Bowls/New Mexico Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/New Orleans Bowl.png` | `12a6def5645fe9ef8c7372f190f4260e129c9b59` | `Master/logos/Bowls/New Orleans Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Palm Bowl.png` | `e05ef7a6b77b864a3e82397ecca94c8b5987ad86` | `Master/logos/Bowls/Palm Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Pelican Bowl.png` | `de9817580fba00f54411775f189ae3666569884c` | `Master/logos/Bowls/Pelican Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Pinstripe Bowl.png` | `1324bdeb2caabba2accb57acd55942a73263b0ee` | `Master/logos/Bowls/Pinstripe Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Poinsettia Bowl.png` | `b14105f47c8d2e764411217f4a16a35f3531fb3e` | `Master/logos/Bowls/Poinsettia Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Stagg Bowl.png` | `e6fe46235fb7619125031ccfb33063c0dadaafd4` | `Master/logos/Bowls/Stagg Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Sun Bowl.png` | `01e1aa43e2ba024348f1133e113c5b242c875131` | `Master/logos/Bowls/Sun Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/TaxSlayer Bowl.png` | `bb09c5d140c3afca7ccfdef1e24b890c7afda85f` | `Master/logos/Bowls/TaxSlayer Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Texas Bowl.png` | `5fe7e5ecd1c712e4cf594fd1fc6df5dba9c88d6d` | `Master/logos/Bowls/Texas Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Vulcan Bowl.png` | `afa198fbadecd82a07a212d622806df514a44d63` | `Master/logos/Bowls/Vulcan Bowl.png` | Identical Git blob |
| `assets/logos/source/Bowls/Zia Bowl.png` | `23ebc7e207838e5ba29b45182032a4beef50e7e1` | `Master/logos/Bowls/Zia Bowl.png` | Identical Git blob |
| `assets/logos/source/CCG/Big East CCG.png` | `2aaa0360e1c1431d45cf334c363565e23bf5f368` | `Master/logos/CCG/Big East CCG.png` | Identical Git blob |
| `assets/logos/source/CCG/Big Sky CCG.png` | `acef89a2c36c666fc37ce4feb399b069510c5bbf` | `Master/logos/CCG/Big Sky CCG.png` | Identical Git blob |
| `assets/logos/source/CCG/Big Ten CCG.png` | `da7f490bffa4a75aded271679071da246e7f2140` | `Master/logos/CCG/Big Ten CCG.png` | Identical Git blob |
| `assets/logos/source/CCG/HBCU CCG.png` | `a536cb7c7a627e8bb8a0ff249b012dddf34530f4` | `Master/logos/CCG/HBCU CCG.png` | Identical Git blob |
| `assets/logos/source/CCG/Independents CCG.png` | `99d35af8a8b6c8bfc90c50bb095bb7904a27797e` | `Master/logos/CCG/Independents CCG.png` | Identical Git blob |
| `assets/logos/source/CCG/Ivy CCG.png` | `579d31432e5ac079e04e238e69ac7e01a87936eb` | `Master/logos/CCG/Ivy CCG.png` | Identical Git blob |
| `assets/logos/source/CCG/Mountain West CCG.png` | `cff04b434c71f7e29e5340f55176a9945dd81985` | `Master/logos/CCG/Mountain West CCG.png` | Identical Git blob |
| `assets/logos/source/CCG/NCAA CCG.png` | `1cff4bb06eda2bf2fe50e63460a8b3a0bdf6f3ad` | `Master/logos/CCG/NCAA CCG.png` | Identical Git blob |
| `assets/logos/source/CCG/Ohio Valley CCG.png` | `8af91a0b1b5770ff3f2d235773829f8c061c7994` | `Master/logos/CCG/Ohio Valley CCG.png` | Identical Git blob |
| `assets/logos/source/CCG/Pac-12 CCG.png` | `48b33341ff4c87566dfcd0b228e003ea6d1b14a2` | `Master/logos/CCG/Pac-12 CCG.png` | Identical Git blob |
| `assets/logos/source/CCG/Pioneer CCG.png` | `b7a9ced75ae89bec20606b596267da8a7800399c` | `Master/logos/CCG/Pioneer CCG.png` | Identical Git blob |
| `assets/logos/source/CCG/SEC CCG.png` | `e4a065e0d78dfc8d1027cf39406e6cbeba655c6c` | `Master/logos/CCG/SEC CCG.png` | Identical Git blob |
| `assets/logos/source/CCG/Wild CCG.png` | `597c6b0e7f5842caf37d38841edacbe03748eacd` | `Master/logos/CCG/Wild CCG.png` | Identical Git blob |
| `assets/logos/source/CCG/retired/Pac-12 CCG 2026-11-17.png` | `6c16b2216bd6fea8b99cbd6ed1707904e5138418` | `Archive/logos/CCG/Pac-12 CCG 2026-11-17.png` | Identical Git blob |
| `assets/logos/source/CCG/retired/Pac-12 CCG previous-web.png` | `06789a528b19c557e4fff3c1e69c31daaeac57ed` | `Archive/logos/CCG/Pac-12 CCG previous-web.png` | Identical Git blob |
| `assets/logos/source/Playoffs/2022.png` | `a4f4a1f3eef2128d7d94e5dc31dfa819404b189f` | `Master/logos/Playoffs/2022.png` | Identical Git blob |
| `assets/logos/source/Playoffs/2023-mark.png` | `d6924008454ced021ebcf040537886922c31b65b` | `Master/logos/Playoffs/2023-mark.png` | Identical Git blob |
| `assets/logos/source/Playoffs/2024.png` | `d7c3eeff354ab9a9dc4ff9cf99742c5d0d502070` | `Master/logos/Playoffs/2024.png` | Identical Git blob |
| `assets/logos/source/Playoffs/Cotton Bowl.png` | `b05fb1de50acda48e4bcedc12edb86702b315a00` | `Master/logos/Playoffs/Cotton Bowl.png` | Identical Git blob |
| `assets/logos/source/Playoffs/Fiesta Bowl.png` | `a7678924153aa3fd44ddccae749f0146e8a4ce65` | `Master/logos/Playoffs/Fiesta Bowl.png` | Identical Git blob |
| `assets/logos/source/Playoffs/National Championship.png` | `da2d94de0c7adcbc396b12f4b23e0825f44561c2` | `Master/logos/Playoffs/National Championship.png` | Identical Git blob |
| `assets/logos/source/Playoffs/Orange Bowl.png` | `08d5acfbe1e287638f5674cbfbec88c41ad09ab1` | `Master/logos/Playoffs/Orange Bowl.png` | Identical Git blob |
| `assets/logos/source/Playoffs/Peach Bowl.png` | `dd5ca7493f05eb703fc4d927605db9c46a5cf6dc` | `Master/logos/Playoffs/Peach Bowl.png` | Identical Git blob |
| `assets/logos/source/Playoffs/Rose Bowl.png` | `3f6b624fa73e1394d11fd74abe1d7af0511cf4b4` | `Master/logos/Playoffs/Rose Bowl.png` | Identical Git blob |
| `assets/logos/source/Playoffs/Sugar Bowl.png` | `7921811642b51baa6527e31d41a53d2958063f01` | `Master/logos/Playoffs/Sugar Bowl.png` | Identical Git blob |
| `assets/logos/source/Playoffs/Trophy w outline.png` | `ac80177cb01583790017c36a38adde1e516a4fc4` | `Master/logos/Playoffs/Trophy w outline.png` | Identical Git blob |
| `assets/logos/source/Playoffs/Trophy.png` | `fb666abc057fdee8bfe86de22584003d810c560f` | `Master/logos/Playoffs/Trophy.png` | Identical Git blob |
| `assets/logos/source/badges/GOTW Postseason.png` | `808842531bc81ff85df1f0efc82a5ecaa17efa5a` | `Master/logos/badges/GOTW Postseason.png` | Identical Git blob |
| `assets/logos/source/badges/GOTW.png` | `d17c7e5244a26c1441c628c39ecca7f5624322b1` | `Master/logos/badges/GOTW.png` | Identical Git blob |
| `assets/logos/source/teams/Akron.png` | `b2cf1fe43a8a1c117182580e5ff500c08b904d67` | `Master/logos/teams/Akron.png` | Identical Git blob |
| `assets/logos/source/teams/Appalachian State.png` | `b9ab62982ceb3e2376ab1f727904bc9af44eb3da` | `Master/logos/teams/Appalachian State.png` | Identical Git blob |
| `assets/logos/source/teams/Arkansas.png` | `e2044866906c9cbaf79d5218224d1f08e37252ca` | `Master/logos/teams/Arkansas.png` | Identical Git blob |
| `assets/logos/source/teams/Ball State.png` | `79aaaf6cde00a51319b9bcb419fedf3ee5e4e39d` | `Master/logos/teams/Ball State.png` | Identical Git blob |
| `assets/logos/source/teams/Bowling Green.png` | `3dca4573cd1f45e9d873fa19bf00b230cf0c0737` | `Master/logos/teams/Bowling Green.png` | Identical Git blob |
| `assets/logos/source/teams/Buffalo.png` | `f65b9293132018b2333d42cb15c874fcf83fc195` | `Master/logos/teams/Buffalo.png` | Identical Git blob |
| `assets/logos/source/teams/Cincinnati.png` | `5bf6f304a596d7560a915d9739731146b4dd2469` | `Master/logos/teams/Cincinnati.png` | Identical Git blob |
| `assets/logos/source/teams/Delaware.png` | `905556778e7f9200ae87018d7d811e334b796669` | `Master/logos/teams/Delaware.png` | Identical Git blob |
| `assets/logos/source/teams/Dixie State.png` | `52a4a8f805d168349dec1f1cdd79646a96d18f46` | `Master/logos/teams/Dixie State.png` | Identical Git blob |
| `assets/logos/source/teams/ECU.png` | `39df6b5fa92819e199a528c5de862b7d85c610f7` | `Master/logos/teams/ECU.png` | Identical Git blob |
| `assets/logos/source/teams/Eastern Kentucky.png` | `034d90965af688b7c6db0ffcdda542e702e669d7` | `Master/logos/teams/Eastern Kentucky.png` | Identical Git blob |
| `assets/logos/source/teams/FGCU.png` | `2e1d5f5dc0ae94f650db8392ea439e095fdb28a3` | `Master/logos/teams/FGCU.png` | Identical Git blob |
| `assets/logos/source/teams/Hampton.png` | `bf743068a40f0049a4b4c6730dd6d09fc00e2108` | `Master/logos/teams/Hampton.png` | Identical Git blob |
| `assets/logos/source/teams/Houston Baptist.png` | `778802c1f27e6855607643530357e6c65570d865` | `Master/logos/teams/Houston Baptist.png` | Identical Git blob |
| `assets/logos/source/teams/Houston Christian.png` | `3d053a26e4f1292ea3e54ba4a419d64045dd70b0` | `Master/logos/teams/Houston Christian.png` | Identical Git blob |
| `assets/logos/source/teams/Houston.png` | `e3040944274aee9347f216c8c2168a466bb13355` | `Master/logos/teams/Houston.png` | Identical Git blob |
| `assets/logos/source/teams/Incarnate Word.png` | `c0af77eb1332b765a8ad779726af5f14ec490438` | `Master/logos/teams/Incarnate Word.png` | Identical Git blob |
| `assets/logos/source/teams/Kent State.png` | `f58a35b3614b5e764c0de6155a5c6f83c12ee046` | `Master/logos/teams/Kent State.png` | Identical Git blob |
| `assets/logos/source/teams/Lamar.png` | `97189db66114bb493452161d7c65b9bb892f2d2e` | `Master/logos/teams/Lamar.png` | Identical Git blob |
| `assets/logos/source/teams/Liberty.png` | `a7d27af5f86d7d86d81f49d903c51a036ba301a0` | `Master/logos/teams/Liberty.png` | Identical Git blob |
| `assets/logos/source/teams/McNeese State.png` | `b50205daf001eb073344d14bbddc836a563fadc2` | `Master/logos/teams/McNeese State.png` | Identical Git blob |
| `assets/logos/source/teams/Miami (OH).png` | `60582cecddb8d584f0e6fa15c69469f27c5efb22` | `Master/logos/teams/Miami (OH).png` | Identical Git blob |
| `assets/logos/source/teams/Missouri State.png` | `fde28925f002eedd31a74215587f8665daaae818` | `Master/logos/teams/Missouri State.png` | Identical Git blob |
| `assets/logos/source/teams/New Mexico State.png` | `9eaacfbd70f978a7e0da654f714c6f93aae685ec` | `Master/logos/teams/New Mexico State.png` | Identical Git blob |
| `assets/logos/source/teams/Nicholls State.png` | `e3a1714fc5c6a6c57c4742da3dfb4f9a1b4840b4` | `Master/logos/teams/Nicholls State.png` | Identical Git blob |
| `assets/logos/source/teams/North Dakota State.png` | `a3a3c679584cbb96f5c5a6b32b4e38271c21374f` | `Master/logos/teams/North Dakota State.png` | Identical Git blob |
| `assets/logos/source/teams/Northwestern State.png` | `d3b83adb2a60bfb64aa12e2006f73b44f6932ed6` | `Master/logos/teams/Northwestern State.png` | Identical Git blob |
| `assets/logos/source/teams/Ohio.png` | `e7daf74c94a548bb494a1653650cee54befaebd4` | `Master/logos/teams/Ohio.png` | Identical Git blob |
| `assets/logos/source/teams/Ole Miss.png` | `19cc89e988ab694c5efdf8b5f338bdec94203703` | `Master/logos/teams/Ole Miss.png` | Identical Git blob |
| `assets/logos/source/teams/Oregon State.png` | `3880cd3badcbeddf02d281223b55ca0998600363` | `Master/logos/teams/Oregon State.png` | Identical Git blob |
| `assets/logos/source/teams/Presbyterian.png` | `b10e494647af57c0f2e6d95e2858aa88f80d11b7` | `Master/logos/teams/Presbyterian.png` | Identical Git blob |
| `assets/logos/source/teams/SMU.png` | `ae5af86046227333145d45993941da81495d738e` | `Master/logos/teams/SMU.png` | Identical Git blob |
| `assets/logos/source/teams/Sacramento State.png` | `811590b1b5a6a3cc2ea0b2fe1a8ec01c66622367` | `Master/logos/teams/Sacramento State.png` | Identical Git blob |
| `assets/logos/source/teams/Sam Houston State.png` | `45d9798422a6726c4934481389edf8505c294023` | `Master/logos/teams/Sam Houston State.png` | Identical Git blob |
| `assets/logos/source/teams/South Dakota.png` | `f7b6d0aca3d9a2762a54582414939ff7a8a2ccbc` | `Master/logos/teams/South Dakota.png` | Identical Git blob |
| `assets/logos/source/teams/Southeastern Louisiana.png` | `337e022d00c47b8c0943779fb082e9c0509d3c8d` | `Master/logos/teams/Southeastern Louisiana.png` | Identical Git blob |
| `assets/logos/source/teams/Stephen F. Austin.png` | `9c1566d95515bfbaba783f25b58075b55ca2bb86` | `Master/logos/teams/Stephen F. Austin.png` | Identical Git blob |
| `assets/logos/source/teams/TCU.png` | `541a6834dbf52beca60348abfb15d97f387ea255` | `Master/logos/teams/TCU.png` | Identical Git blob |
| `assets/logos/source/teams/Toledo.png` | `dac85ca22004b6da85b550a2720f3e030b755f4e` | `Master/logos/teams/Toledo.png` | Identical Git blob |
| `assets/logos/source/teams/UAB.png` | `baf1bb6ac9def648fd81f646310bcf9a179d0416` | `Master/logos/teams/UAB.png` | Identical Git blob |
| `assets/logos/source/teams/UMass.png` | `ae39caba775e95e982801e54794a1f2c684f64b5` | `Master/logos/teams/UMass.png` | Identical Git blob |
| `assets/logos/source/teams/Weber State.png` | `2f2918e3b7252d3122f4851562c6ce4cb5bed406` | `Master/logos/teams/Weber State.png` | Identical Git blob |
| `assets/logos/source/teams/Western Michigan.png` | `36eaadad5dd170e613923969294245a3507c8180` | `Master/logos/teams/Western Michigan.png` | Identical Git blob |
| `assets/logos/source/teams/alt-dark/Boston College.png` | `72dcc7edce007f8e97e0df91488c6d4a9e8989cd` | `Master/logos/teams/alt-dark/Boston College.png` | Identical Git blob |
| `assets/logos/source/teams/alt-dark/California.png` | `5df4d492b134621228da7406f347c7025f754295` | `Master/logos/teams/alt-dark/California.png` | Identical Git blob |
| `assets/logos/source/teams/alt-dark/Central Arkansas.png` | `86ee5fd77a5b483287eb38604720fe95f7139989` | `Master/logos/teams/alt-dark/Central Arkansas.png` | Identical Git blob |
| `assets/logos/source/teams/alt-dark/Duke.png` | `d605f78b9174bc07ffce0ac4ffe41348a6e34881` | `Master/logos/teams/alt-dark/Duke.png` | Identical Git blob |
| `assets/logos/source/teams/alt-dark/Eastern Kentucky.png` | `3e0369222b197e111ca7b7e9238d6d73be46fed8` | `Master/logos/teams/alt-dark/Eastern Kentucky.png` | Identical Git blob |
| `assets/logos/source/teams/alt-dark/Georgetown.png` | `1b0f9e85440ee0144907a9e89220852f41da321b` | `Master/logos/teams/alt-dark/Georgetown.png` | Identical Git blob |
| `assets/logos/source/teams/alt-dark/Incarnate Word.png` | `76b99e4670e97bbeba90cf58235d329470cffa01` | `Master/logos/teams/alt-dark/Incarnate Word.png` | Identical Git blob |
| `assets/logos/source/teams/alt-dark/Iowa.png` | `7dd85b49765d35cccf1dfe4f4ca11abc6d927963` | `Master/logos/teams/alt-dark/Iowa.png` | Identical Git blob |
| `assets/logos/source/teams/alt-dark/Kansas State.png` | `ce9676c4812eec829d4c45450026fe4d50fc41cc` | `Master/logos/teams/alt-dark/Kansas State.png` | Identical Git blob |
| `assets/logos/source/teams/alt-dark/Kentucky.png` | `6195476ca0b683bc4ab28bec7142d3d70899bb6e` | `Master/logos/teams/alt-dark/Kentucky.png` | Identical Git blob |
| `assets/logos/source/teams/alt-dark/LSU.png` | `2329fa4dac6b04b8cb6095fe977ea9a16217d1fd` | `Master/logos/teams/alt-dark/LSU.png` | Identical Git blob |
| `assets/logos/source/teams/alt-dark/Minnesota.png` | `baae6e8521d909d4b20af382f27971bf9a05e3ed` | `Master/logos/teams/alt-dark/Minnesota.png` | Identical Git blob |
| `assets/logos/source/teams/alt-dark/Nevada.png` | `6c2103d55e5a8e59a40e5ca7910094c1bc83936f` | `Master/logos/teams/alt-dark/Nevada.png` | Identical Git blob |
| `assets/logos/source/teams/alt-dark/North Dakota State.png` | `6be73442af2efb5a476bc06f418b509a37c7cfa9` | `Master/logos/teams/alt-dark/North Dakota State.png` | Identical Git blob |
| `assets/logos/source/teams/alt-dark/Oregon.png` | `38555fa149f922e1ccbb762ba5f955b990aa2278` | `Master/logos/teams/alt-dark/Oregon.png` | Identical Git blob |
| `assets/logos/source/teams/alt-dark/TCU.png` | `0a1dfe3f43fe3d24bf2e3db49bca4a075d582401` | `Master/logos/teams/alt-dark/TCU.png` | Identical Git blob |
| `assets/logos/source/teams/alt-dark/Tulsa.png` | `3ee39ef2f693c61685c3dff219ea0a0a8943d07d` | `Master/logos/teams/alt-dark/Tulsa.png` | Identical Git blob |
| `assets/logos/source/teams/alt-dark/UAB.png` | `aab8e31c89363f7022c419b7fe125349400a3471` | `Master/logos/teams/alt-dark/UAB.png` | Identical Git blob |
| `assets/logos/source/teams/alt-dark/Utah State.png` | `70516c91eddc3aafff1abb76cb7befe14971132f` | `Master/logos/teams/alt-dark/Utah State.png` | Identical Git blob |
