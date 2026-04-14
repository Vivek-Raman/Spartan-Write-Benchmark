\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{SJSUthesis}[2026/03/16 Custom Thesis Class overriding IEEEtran]

% Pass standard options to IEEEtran. Force 12pt and onecolumn.
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{IEEEtran}}
\ProcessOptions\relax
\LoadClass[12pt, onecolumn, journal]{IEEEtran}

% ==========================================
% REQUIRED PACKAGES
% ==========================================
\RequirePackage[left=1.25in, right=1in, top=1.25in, bottom=1.25in]{geometry} % Rule 3
\RequirePackage{setspace} % Rule 5
\RequirePackage[document]{ragged2e} % Rule 3: Left justified without terrible hyphenation gaps
\RequirePackage{titlesec} % Rule 7: Section breaks
\RequirePackage{etoolbox} % Rule 8: Patching environments
\RequirePackage{mathptmx} % Rule 4: Professional 12pt font (Times clone)
\RequirePackage{graphicx} % For figures
\RequirePackage{caption} % Rule 10: Caption formatting
\RequirePackage{tocloft} % Rule 12: ToC styling

% ==========================================
% RULE 3 & 4: TEXT FORMATTING
% ==========================================
\hyphenpenalty=10000
\exhyphenpenalty=10000
\RaggedRight % Enforces left-justification only
\sloppy 
\setlength{\emergencystretch}{3em}

% ==========================================
% RULE 5: SPACING
% ==========================================
\doublespacing

% Patch block quotes to be single-spaced
\AtBeginEnvironment{quote}{\singlespacing}
\AtBeginEnvironment{quotation}{\singlespacing}

% ==========================================
% RULE 6: INDENTATION
% ==========================================
\setlength{\parindent}{0.25in}
\setlength{\RaggedRightParindent}{0.25in}

% ==========================================
% RULE 7: NEW PAGES FOR SECTIONS
% ==========================================
% Since IEEEtran uses \section instead of \chapter for top-level divisions:
\newcommand{\sectionbreak}{\clearpage}

% ==========================================
% RULE 8: BIBLIOGRAPHY SPACING
% ==========================================
% Single-line spaced for each entry, double-spaced between entries.
\patchcmd{\thebibliography}
  {\list}
  {\singlespacing\list}
  {}
  {}
\apptocmd{\thebibliography}{%
  \setlength{\parskip}{1\baselineskip} % Double space between items
  \setlength{\itemsep}{0pt}
}{}{}

% ==========================================
% RULE 10: CAPTIONS AND FLOATS
% ==========================================
% Ensure captions are single spaced. 8pt is permitted inside tables/figures.
\captionsetup{font={singlespacing, small}, parindent=0pt}
\captionsetup[figure]{justification=centering, parindent=0pt, singlelinecheck=true}
\AtBeginEnvironment{table}{%
  \singlespacing\small
  \setlength{\parindent}{0pt}%
  \setlength{\RaggedRightParindent}{0pt}%
} % Sets table text smaller; no paragraph indent inside float
\AtBeginEnvironment{table*}{%
  \singlespacing\small
  \setlength{\parindent}{0pt}%
  \setlength{\RaggedRightParindent}{0pt}%
}
\AtBeginEnvironment{figure}{%
  \singlespacing
  \setlength{\parindent}{0pt}%
  \setlength{\RaggedRightParindent}{0pt}%
}
\AtBeginEnvironment{figure*}{%
  \singlespacing
  \setlength{\parindent}{0pt}%
  \setlength{\RaggedRightParindent}{0pt}%
}
% ==========================================
% RULE 12: TABLE OF CONTENTS DEPTH
% ==========================================
\setcounter{tocdepth}{3} % Up to Level 3 subheadings

% ==========================================
% RULES 13 & 14: FRONTMATTER & NUMBERING
% ==========================================
% IEEEtran lacks native \frontmatter and \mainmatter commands. We build them.

\newcommand{\makefrontmatter}{
    \pagenumbering{roman}
}

\newcommand{\makemainmatter}{
    \clearpage
    \pagenumbering{arabic}
    \setcounter{page}{1}
}

% Mandatory Unnumbered Pages
\newcommand{\thesistitlepage}[4]{
    \clearpage
    \thispagestyle{empty}
    \begin{center}
        \vspace*{2in}
        {\Large \textbf{#1}\par} % Title
        \vspace{1in}
        A Thesis Presented to \\ #2 \par % University
        \vspace{1in}
        By \\ #3 \par % Author
        \vspace{1in}
        #4 \par % Date
    \end{center}
    \clearpage
}

\newcommand{\copyrightpage}[1]{
    \clearpage
    \thispagestyle{empty}
    \vspace*{4in}
    \begin{center}
        Copyright \textcopyright\ #1
    \end{center}
    \clearpage
}

\newcommand{\signaturepage}{
    \clearpage
    \thispagestyle{empty}
    \vspace*{2in}
    \begin{center}
        [Replace this page with the Official SJSU Signature Page]
    \end{center}
    \clearpage
}

\newcommand{\abstractpage}[1]{
    \clearpage
    \thispagestyle{empty}
    \begin{center}
        \textbf{ABSTRACT}
    \end{center}
    \doublespacing
    #1
    \clearpage
}

% Trigger for page v numbering
\newcommand{\startprelimnumbering}{
    \setcounter{page}{5} % First numbered page must be v
}