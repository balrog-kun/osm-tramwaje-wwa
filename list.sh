#! /bin/bash

i=1
num=x
tiles=

output () {
	if [[ "$num" != x ]]; then
		[[ "$tiles" == "" ]] && tiles="40x40"
#		echo "|-----"
#		echo "|$i."
#		echo "|$ulica"
#		echo "|$przyst"
#		echo "|$num"
#		echo "|$tiles"
#		echo "|"
		echo "{"
		echo "	\"strt\": \"$ulica\","
		echo "	\"stop\": \"$przyst\","
		echo "	\"num\":  \"$num\","
		echo "	\"tile\": \"$tiles\","
		echo "},"

		i=$((i + 1))
		num=x
		tiles=
	fi
}

while read -r line; do
	case "$line" in
		---* )
			tiles="${line:3}"
			;;
		--* )
			output
			num="${line:2}"
			;;
		-* )
			output
			przyst="${line:1}"
			;;
		* )
			output
			ulica="${line}"
			;;
	esac
done
output
