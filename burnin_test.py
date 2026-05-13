#!/usr/bin/env python
import sys
import pandas as pd
import matplotlib.pyplot as plt

def latex_formatting(ax, fontsize=11):
    ax.tick_params(which='both', direction='in', top=True, right=True, 
                   bottom=True, left=True, labelsize=fontsize)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontsize(fontsize)

def main():
    if len(sys.argv) != 3:
        print("Usage: python burnin_test.py <bayes.dat> <output.pdf>")
        sys.exit(1)
    
    bayes_file = sys.argv[1]
    output_file = sys.argv[2]
    
    data = pd.read_csv(bayes_file, sep='\s+', comment='#')
    nsamples = data.iloc[:, 0]
    chi2 = data.iloc[:, 31]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(nsamples, chi2, s=1, color='blue', alpha=0.5)
    
    ax.set_xlabel('N samples', fontsize=12)
    ax.set_ylabel(r'$\chi^2$', fontsize=12)
    latex_formatting(ax, fontsize=11)
    
    fig.tight_layout()
    fig.savefig(output_file, dpi=300)
    print(f"Saved: {output_file}")

if __name__ == '__main__':
    main()
