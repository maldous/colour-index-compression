// Transform-only driver for the public fx2-cmix reference implementation.
// The included upstream code is by Kaido Orav, Byron Knoll and credited
// contributors, under its accompanying GPL licence. No model is run here.
#include <bits/stdc++.h>
#include <unistd.h>
#include "phda9_preprocess.h"
#include "article_reorder.h"
#include "misc.h"

int main(int argc, char **argv) {
  if (argc == 3 && std::string(argv[1]) == "encode") {
    split4Comp(argv[2]);
    reorder();
    phda9_prepr();
    cat(".main_phda9prepr", ".intro", "un1");
    cat("un1", ".coda", ".ready4cmix");
    return 0;
  }
  if (argc == 2 && std::string(argv[1]) == "decode") {
    split4Decomp();
    phda9_resto();
    sort();
    cat(".intro_decomp", ".main_decomp_restored_sorted", "un1_d");
    cat("un1_d", ".coda_decomp", "enwik9_restored");
    return 0;
  }
  std::cerr << "usage: transform encode canonical-enwik9 | transform decode\n";
  return 2;
}
