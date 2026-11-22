/*
 * The reading half of `of_date_candidates.py` for one candidate: SuperNOVAS, with the SPICE Toolkit as
 * its ephemeris reader. A recorder: it calls the library's own entry points and prints what they return.
 *
 * Protocol (stdin -> stdout, one line per request, every double as its 16-hex-digit IEEE-754 pattern):
 *
 *   start        -> "V <library version> <toolkit version>"   after the one kernel (argv[1]) is loaded
 *   M <jd1> <jd2>
 *                -> "M" + mean_obliq, e_tilt (mean, true, equation of the equinoxes, dpsi, deps),
 *                   nutation_angles (dpsi, deps), iau2000a (dpsi, deps), and gcrs_to_tod applied to the three
 *                   unit vectors (nine elements, row-major: element [i][k] is component i of image k)
 *   A <jd_tdb> <naif id> <deflection 0|1>
 *                -> "A" + ra, dec, dis, r_hat[3] of novas_sky_pos in the true equator and equinox of date,
 *                   and equ2ecl's ecliptic longitude and latitude of that ra and dec, true equator
 *   any failure  -> "E <request> <return code>" and exit status 3; nothing after it is read
 *
 * Arguments a request does not carry are fixed here and printed by the caller into its record: full
 * accuracy everywhere; a geocentric observer; the time given as TDB with no leap seconds and no UT1
 * offset (a geocentric place of date asks for neither); polar offsets zero; deflection by the library's
 * default full-accuracy set of bodies, or by none. `jd1 + jd2` is the single date a one-argument entry
 * point takes; `((jd1 - 2451545.0) + jd2) / 36525.0` is the centuries the one centuries-argument entry
 * point takes. Nothing else is computed here.
 */

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "novas.h"
#include "novas-cspice.h"
#include "cspice/SpiceUsr.h"

static double from_bits(const char *hex) {
  uint64_t u = strtoull(hex, NULL, 16);
  double d;
  memcpy(&d, &u, sizeof d);
  return d;
}

static void put(double d) {
  uint64_t u;
  memcpy(&u, &d, sizeof u);
  printf(" %016" PRIx64, u);
}

static void fail(const char *request, int code) {
  printf("E %s %d\n", request, code);
  fflush(stdout);
  exit(3);
}

static void model(double jd1, double jd2) {
  const double jd = jd1 + jd2;
  const double t = ((jd1 - 2451545.0) + jd2) / 36525.0;
  double mobl, tobl, ee, dpsi, deps, na_dpsi, na_deps, a_dpsi, a_deps;
  double unit[3][3] = { { 1.0, 0.0, 0.0 }, { 0.0, 1.0, 0.0 }, { 0.0, 0.0, 1.0 } };
  double image[3][3];
  int k, i, rc;

  const double mean = mean_obliq(jd);
  if((rc = e_tilt(jd, NOVAS_FULL_ACCURACY, &mobl, &tobl, &ee, &dpsi, &deps)) != 0) fail("e_tilt", rc);
  if((rc = nutation_angles(t, NOVAS_FULL_ACCURACY, &na_dpsi, &na_deps)) != 0) fail("nutation_angles", rc);
  if((rc = iau2000a(jd1, jd2, &a_dpsi, &a_deps)) != 0) fail("iau2000a", rc);
  for(k = 0; k < 3; k++)
    if((rc = gcrs_to_tod(jd, NOVAS_FULL_ACCURACY, unit[k], image[k])) != 0) fail("gcrs_to_tod", rc);

  printf("M");
  put(mean);
  put(mobl); put(tobl); put(ee); put(dpsi); put(deps);
  put(na_dpsi); put(na_deps);
  put(a_dpsi); put(a_deps);
  for(i = 0; i < 3; i++)
    for(k = 0; k < 3; k++)
      put(image[k][i]);
  printf("\n");
}

static void apparent(double jd_tdb, long naif, int deflection) {
  novas_timespec time;
  observer obs;
  novas_frame frame;
  object body;
  sky_pos pos;
  double elon, elat;
  int rc;

  grav_bodies_full_accuracy = deflection ? DEFAULT_GRAV_BODIES_FULL_ACCURACY : 0;
  if((rc = novas_set_time(NOVAS_TDB, jd_tdb, 0, 0.0, &time)) != 0) fail("novas_set_time", rc);
  if((rc = make_observer_at_geocenter(&obs)) != 0) fail("make_observer_at_geocenter", rc);
  if((rc = novas_make_frame(NOVAS_FULL_ACCURACY, &obs, &time, 0.0, 0.0, &frame)) != 0) fail("novas_make_frame", rc);
  if((rc = make_ephem_object("target", naif, &body)) != 0) fail("make_ephem_object", rc);
  if((rc = novas_sky_pos(&body, &frame, NOVAS_TOD, &pos)) != 0) fail("novas_sky_pos", rc);
  if((rc = equ2ecl(novas_get_time(&time, NOVAS_TT), NOVAS_TRUE_EQUATOR, NOVAS_FULL_ACCURACY, pos.ra, pos.dec,
                   &elon, &elat)) != 0) fail("equ2ecl", rc);

  printf("A");
  put(pos.ra); put(pos.dec); put(pos.dis);
  put(pos.r_hat[0]); put(pos.r_hat[1]); put(pos.r_hat[2]);
  put(elon); put(elat);
  printf("\n");
}

int main(int argc, char **argv) {
  char line[256], kind[4], a[32], b[32], c[32];
  SpiceChar *toolkit;
  int rc;

  if(argc != 2) {
    fprintf(stderr, "usage: %s <kernel>\n", argv[0]);
    return 2;
  }
  if((rc = cspice_add_kernel(argv[1])) != 0) fail("cspice_add_kernel", rc);
  if((rc = novas_use_cspice()) != 0) fail("novas_use_cspice", rc);
  toolkit = (SpiceChar *) tkvrsn_c("TOOLKIT");
  printf("V %d.%d.%d%s %s\n", SUPERNOVAS_MAJOR_VERSION, SUPERNOVAS_MINOR_VERSION, SUPERNOVAS_PATCHLEVEL,
         SUPERNOVAS_RELEASE_STRING, toolkit);
  fflush(stdout);

  while(fgets(line, sizeof line, stdin)) {
    int n = sscanf(line, "%3s %31s %31s %31s", kind, a, b, c);
    if(n == 3 && strcmp(kind, "M") == 0) model(from_bits(a), from_bits(b));
    else if(n == 4 && strcmp(kind, "A") == 0) apparent(from_bits(a), strtol(b, NULL, 10), atoi(c));
    else fail("unparsed", -1);
    fflush(stdout);
  }
  return 0;
}
