/*
 * The frame of date by the International Astronomical Union's standard models, as computed by the IAU SOFA
 * library, at a two-part TT handed in: a driver that passes each given TT to the library and writes back every
 * double it returns.
 *
 * This program uses routines and computations provided by SOFA under license; it does not itself constitute
 * software provided by and/or endorsed by SOFA. It contains no SOFA source code: it calls the library's routines,
 * unmodified, from a library built from SOFA's own distribution, and writes their results down.
 *
 * Input (stdin): one line per instant, "<tt1> <tt2>", each the 16 lowercase hex digits of an IEEE-754 double.
 * Output (stdout): a first line "V standards_at_tt 1", then per input line one line
 *   T <tt1> <tt2> <obl06> <dpsi> <deps> <true_obliquity> <r00> <r01> ... <r22>
 * every value as the 16 hex digits of its double, in that order, where:
 *   obl06          = iauObl06(tt1, tt2)                               (radians)
 *   dpsi, deps     = iauNut06a(tt1, tt2)                              (radians)
 *   true_obliquity = obl06 + deps                                     (one IEEE-754 addition)
 *   r[i][j]        = iauPnm06a(tt1, tt2), row i, column j, row-major  (v_date = r v_GCRS)
 * ⛔ The time argument is the caller's: no conversion between time scales is made here.
 * A line "E <reason>" and a non-zero exit on any failure.
 */

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "sofa.h"

static int parse_hex_double(const char *text, double *out) {
    uint64_t word = 0;
    if (strlen(text) != 16) return 0;
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

static void write_double(double x) {
    uint64_t word;
    memcpy(&word, &x, sizeof word);
    printf(" %016" PRIx64, word);
}

int main(void) {
    char line[128];
    printf("V standards_at_tt 1\n");
    while (fgets(line, sizeof line, stdin)) {
        line[strcspn(line, "\r\n")] = '\0';
        if (line[0] == '\0') continue;
        char first[64], second[64], extra[2];
        if (sscanf(line, "%63s %63s %1s", first, second, extra) != 2) {
            printf("E not two bit patterns: %s\n", line);
            return 2;
        }
        double tt1, tt2;
        if (!parse_hex_double(first, &tt1) || !parse_hex_double(second, &tt2)) {
            printf("E not a double's bit pattern: %s\n", line);
            return 2;
        }
        double eps0 = iauObl06(tt1, tt2);
        double dpsi, deps;
        iauNut06a(tt1, tt2, &dpsi, &deps);
        double epst = eps0 + deps;
        double r[3][3];
        iauPnm06a(tt1, tt2, r);
        printf("T");
        write_double(tt1);
        write_double(tt2);
        write_double(eps0);
        write_double(dpsi);
        write_double(deps);
        write_double(epst);
        for (int i = 0; i < 3; i++)
            for (int j = 0; j < 3; j++) write_double(r[i][j]);
        printf("\n");
    }
    return 0;
}
