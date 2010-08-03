# This awk script parses http://gcn.gsfc.nasa.gov/fermi_grbs.html
# and generates an XEphem file for use with PyEphem

# No built in absolute value... grr...
function abs(x)
{
  if(x < 0)
    return x * -1
  else
    return x
}

# We will want to use the tag demarcators as field delimiters
BEGIN { FS = "[<>]" }

# The data is a presented in an HTML table.  
# The entries have a uniform structure, with fields as indicated:
{ if (/<tr align=left>/) 
    { 
      getline
      
      # If we are in a field header, skip
      if (/<th.*/) next
      
      # Random garbage line
      if (/<td><a href=other\/.fermi>/) next

      # First print 
      # "# trigger_number number date time message_type ra dec error"
      # then print 
      # "trigger_number,f|t,ra*,dec*"
      # where ra* and dec* are in xephem format
      printf "# %s ", $5
      trigger_number = $5
     
      # date
      getline
      printf "20%s ", $3

      # time UT
      getline
      printf "%s ", $3
    
      # Message Type
      getline
      printf "%s ", $3
      
      # Right Ascension
      # (we will format this later)
      getline
      printf "%s ", $3
      ra=$3 
      
      # Declination
      # (we will formate this later)
      getline
      printf "%s ", $3
      dec=$3 
      
      # Error
      getline
      printf "%s\n", $3 
      
      # We now print trigger_number-RA-DEC and the object type
      # f means fixed
      # Y means supernova
      printf "fermi-%s-%s-%s,f|Y,", trigger_number, ra, dec

      # We now print RA in H:M:S format
      printf "%02i:%02i:%05.2f,",\
      ra/15, (ra*4)%60, (ra*240)%60 

      # We now print Dec in D:M:S format
      printf "%i:%02i:%05.2f,",\
      dec, abs(dec*60)%60, abs(dec*3600)%60 
      
      # Fermi uses 2000 as its epoc
      printf "2000\n"
    }
}
