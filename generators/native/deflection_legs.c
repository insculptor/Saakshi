/*
 * Light deflection and aberration by the IAU SOFA library, for a source at a finite distance: a driver that hands
 * each case's geometry to the library's routines and writes back every double they return.
 *
 * This program uses routines and computations provided by SOFA under license; it does not itself constitute
 * software provided by and/or endorsed by SOFA. It contains no SOFA source code: it calls the library's routines,
 * unmodified, from a library built from SOFA's own distribution, and writes their results down.
 *
 * Input (stdin): one case per line, every number the 16 lowercase hex digits of its IEEE-754 double:
 *   C <id> <p0 p1 p2> <v0 v1 v2> <s> <bm1> <n> then n times: <bm> <q0 q1 q2> <e0 e1 e2> <em> <dlim>
 * where p is the unit direction observer -> source, v the observer's barycentric velocity in units of c, s the
 * Sun-observer distance (au), bm1 the reciprocal Lorentz factor, and for each deflector, in the order given: bm its
 * mass (solar masses), q the unit direction body -> source, e the unit direction body -> observer, em the
 * body-observer distance (au), dlim the deflection limiter. <id> is an integer, written as given.
 * Output (stdout): a first line "V deflection_legs 1", then per case one line
 *   L <id> <natural direction, 3> <proper direction with deflection, 3> <proper direction without, 3>
 *       <proper direction without, Sun distance given as S_FAR, 3>
 * where the natural direction is p after iauLd for each deflector in turn (p itself where n = 0), the first proper
 * direction iauAb applied to it, the second iauAb applied to p, and the third iauAb applied to p with s = S_FAR.
 * A line "E <reason>" and a non-zero exit on any failure.
 */

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "sofa.h"

#define S_FAR 1.0e300
#define MAX_BODIES 16

static int read_double(double *out) {
    char text[32];
    if (scanf("%31s", text) != 1 || strlen(text) != 16) return 0;
    uint64_t word = 0;
    for (int k = 0; k < 16; k++) {
        char c = text[k];
        int v;
        if (c >= '0' && c <= '9') v = c - '0';
        else if (c >= 'a' && c <= 'f') v = 10 + c - 'a';
        else return 0;
        word = (word << 4) | (uint64_t)v;
    }
    memcpy(out, &word, sizeof word);
    return 1;
}

static int read_vector(double out[3]) {
    return read_double(&out[0]) && read_double(&out[1]) && read_double(&out[2]);
}

static void write_vector(const double x[3]) {
    for (int k = 0; k < 3; k++) {
        uint64_t word;
        memcpy(&word, &x[k], sizeof word);
        printf(" %016" PRIx64, word);
    }
}

int main(void) {
    char tag[4];
    printf("V deflection_legs 1\n");
    while (scanf("%3s", tag) == 1) {
        long id;
        int n;
        double p[3], v[3], s, bm1;
        if (strcmp(tag, "C") != 0 || scanf("%ld", &id) != 1 || !read_vector(p) || !read_vector(v) ||
            !read_double(&s) || !read_double(&bm1) || scanf("%d", &n) != 1 || n < 0 || n > MAX_BODIES) {
            printf("E a case line that does not parse\n");
            return 2;
        }
        double natural[3] = {p[0], p[1], p[2]};
        for (int k = 0; k < n; k++) {
            double bm, q[3], e[3], em, dlim, out[3];
            if (!read_double(&bm) || !read_vector(q) || !read_vector(e) || !read_double(&em) || !read_double(&dlim)) {
                printf("E a deflector of case %ld does not parse\n", id);
                return 3;
            }
            iauLd(bm, natural, q, e, em, dlim, out);
            natural[0] = out[0];
            natural[1] = out[1];
            natural[2] = out[2];
        }
        double with_deflection[3], without[3], without_far[3];
        iauAb(natural, v, s, bm1, with_deflection);
        iauAb(p, v, s, bm1, without);
        iauAb(p, v, S_FAR, bm1, without_far);
        printf("L %ld", id);
        write_vector(natural);
        write_vector(with_deflection);
        write_vector(without);
        write_vector(without_far);
        printf("\n");
    }
    return 0;
}
